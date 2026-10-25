from __future__ import annotations

import ipaddress
import json
from collections.abc import Mapping
from typing import Any

import govor_launcher.network as network
import pytest
from govor_launcher.network import (
    LanInterface,
    _parse_inventory,
    discover_lan_interfaces,
    eligible_lan_interfaces,
    select_lan_interface,
)


def _interface(
    address: str,
    *,
    alias: str = "Ethernet",
    status: str = "Up",
    hardware: bool = True,
    virtual: bool = False,
    category: str | None = "Private",
    gateway: str | None = "192.168.1.1",
    interface_metric: int | None = 25,
    route_metric: int | None = 0,
    index: int = 7,
) -> LanInterface:
    return LanInterface(
        address=ipaddress.IPv4Address(address),
        prefix_length=24,
        interface_index=index,
        interface_alias=alias,
        interface_description=f"{alias} adapter",
        adapter_status=status,
        hardware_interface=hardware,
        virtual=virtual,
        network_category=category,
        default_gateway=ipaddress.IPv4Address(gateway) if gateway else None,
        interface_metric=interface_metric,
        route_metric=route_metric,
    )


def _inventory_item(**changes: Any) -> Mapping[str, Any]:
    item: dict[str, Any] = {
        "interface_index": 7,
        "interface_alias": "Ethernet",
        "interface_description": "Ethernet adapter",
        "adapter_status": "Up",
        "hardware_interface": True,
        "virtual": False,
        "network_category": "Private",
        "address": "192.168.1.20",
        "prefix_length": 24,
        "default_gateway": "192.168.1.1",
        "interface_metric": 25,
        "route_metric": 0,
    }
    item.update(changes)
    return item


def test_windows_inventory_parses_a_physical_private_adapter() -> None:
    result = _parse_inventory([_inventory_item()])

    assert result == (_interface("192.168.1.20"),)


def test_windows_discovery_runs_the_bounded_static_inventory_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def fake_run(command: list[str], **options: Any) -> Any:
        observed.update(command=command, options=options)
        return network.subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps([_inventory_item()]).encode(),
            stderr=b"",
        )

    monkeypatch.setattr(network.os, "name", "nt")
    monkeypatch.setattr(network.subprocess, "run", fake_run)

    result = discover_lan_interfaces()

    assert result == (_interface("192.168.1.20"),)
    assert observed["command"][:5] == [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
    ]
    assert observed["options"]["timeout"] == 15


def test_windows_discovery_fails_closed_when_inventory_command_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(network.os, "name", "nt")
    monkeypatch.setattr(
        network.subprocess,
        "run",
        lambda *args, **kwargs: network.subprocess.CompletedProcess(args, 1, b"", b"denied"),
    )

    with pytest.raises(RuntimeError, match="could not inspect Windows network adapters"):
        discover_lan_interfaces()


def test_windows_discovery_rejects_unbounded_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(network.os, "name", "nt")
    monkeypatch.setattr(
        network.subprocess,
        "run",
        lambda *args, **kwargs: network.subprocess.CompletedProcess(
            args, 0, b" " * (256 * 1024 + 1), b""
        ),
    )

    with pytest.raises(RuntimeError, match="exceeded its size limit"):
        discover_lan_interfaces()


def test_windows_inventory_rejects_malformed_values() -> None:
    with pytest.raises(RuntimeError, match="item 0 is invalid"):
        _parse_inventory([_inventory_item(interface_metric=True)])


@pytest.mark.parametrize(
    ("candidate", "reason"),
    [
        (_interface("192.168.1.20", status="Disconnected"), "not connected"),
        (_interface("192.168.1.20", hardware=False, virtual=True), "virtual"),
        (_interface("169.254.1.20"), "not a private RFC1918"),
        (_interface("192.168.1.20", category="Public"), "Public, not Private"),
    ],
)
def test_unsafe_interfaces_are_not_eligible(
    candidate: LanInterface,
    reason: str,
) -> None:
    assert reason in (candidate.eligibility_error or "")
    assert eligible_lan_interfaces([candidate]) == ()


def test_default_selection_uses_the_lowest_windows_route_metric() -> None:
    ethernet = _interface(
        "192.168.1.20", alias="Ethernet", interface_metric=25, route_metric=0, index=7
    )
    wifi = _interface("192.168.1.21", alias="Wi-Fi", interface_metric=50, route_metric=0, index=9)

    assert select_lan_interface([wifi, ethernet]) == ethernet


def test_explicit_address_selects_another_eligible_physical_adapter() -> None:
    ethernet = _interface("192.168.1.20", alias="Ethernet", index=7)
    wifi = _interface("192.168.1.21", alias="Wi-Fi", index=9)

    assert select_lan_interface([ethernet, wifi], "192.168.1.21") == wifi


def test_explicit_address_cannot_override_the_private_profile_gate() -> None:
    public = _interface("192.168.1.20", category="Public")

    with pytest.raises(RuntimeError, match="not safe to advertise.*Public"):
        select_lan_interface([public], "192.168.1.20")


def test_no_eligible_address_explains_the_windows_profile_fix() -> None:
    public = _interface("192.168.1.20", category="Public")

    with pytest.raises(RuntimeError, match="set its Windows network profile to Private"):
        select_lan_interface([public])


def test_inventory_shape_stays_json_serializable_for_fixture_review() -> None:
    encoded = json.dumps([_inventory_item()])

    assert _parse_inventory(json.loads(encoded))[0].interface_alias == "Ethernet"
