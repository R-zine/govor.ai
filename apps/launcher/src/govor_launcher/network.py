from __future__ import annotations

import ipaddress
import json
import os
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

_MAX_INVENTORY_BYTES = 256 * 1024
_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(prefix) for prefix in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)

# Windows PowerShell 5.1 and the NetTCPIP module are present on every supported release target.
# The script is application-owned and accepts no interpolated/user-controlled input.
_NETWORK_INVENTORY_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$routes = @(
    Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' `
        -PolicyStore ActiveStore -ErrorAction SilentlyContinue
)
$items = @(Get-NetIPConfiguration -All | ForEach-Object {
    $configuration = $_
    $matchingRoutes = @(
        $routes | Where-Object { $_.InterfaceIndex -eq $configuration.InterfaceIndex }
    )
    $routeMetric = if ($matchingRoutes.Count -gt 0) {
        [int](($matchingRoutes | Measure-Object -Property RouteMetric -Minimum).Minimum)
    } else {
        $null
    }
    foreach ($ip in @($configuration.IPv4Address)) {
        [pscustomobject]@{
            interface_index = [int]$configuration.InterfaceIndex
            interface_alias = [string]$configuration.InterfaceAlias
            interface_description = [string]$configuration.InterfaceDescription
            adapter_status = [string]$configuration.NetAdapter.Status
            hardware_interface = [bool]$configuration.NetAdapter.HardwareInterface
            virtual = [bool]$configuration.NetAdapter.Virtual
            network_category = if ($null -ne $configuration.NetProfile) {
                [string]$configuration.NetProfile.NetworkCategory
            } else {
                $null
            }
            address = [string]$ip.IPAddress
            prefix_length = [int]$ip.PrefixLength
            default_gateway = if ($null -ne $configuration.IPv4DefaultGateway) {
                [string](@($configuration.IPv4DefaultGateway)[0].NextHop)
            } else {
                $null
            }
            interface_metric = [int]$configuration.NetIPv4Interface.InterfaceMetric
            route_metric = $routeMetric
        }
    }
})
ConvertTo-Json -InputObject $items -Compress
"""


@dataclass(frozen=True)
class LanInterface:
    address: ipaddress.IPv4Address
    prefix_length: int
    interface_index: int
    interface_alias: str
    interface_description: str
    adapter_status: str
    hardware_interface: bool
    virtual: bool
    network_category: str | None
    default_gateway: ipaddress.IPv4Address | None
    interface_metric: int | None
    route_metric: int | None

    @property
    def eligibility_error(self) -> str | None:
        if self.adapter_status.casefold() != "up":
            return "adapter is not connected"
        if not self.hardware_interface or self.virtual:
            return "adapter is virtual"
        if not _is_rfc1918(self.address):
            return "address is not a private RFC1918 address"
        if (self.network_category or "").casefold() != "private":
            category = self.network_category or "unidentified"
            return f"Windows network profile is {category}, not Private"
        return None

    @property
    def route_preference(self) -> tuple[int, int, int, int]:
        has_default_route = self.default_gateway is not None and self.route_metric is not None
        route_metric = self.route_metric if self.route_metric is not None else 1_000_000
        interface_metric = self.interface_metric if self.interface_metric is not None else 1_000_000
        return (
            0 if has_default_route else 1,
            route_metric + interface_metric,
            self.interface_index,
            int(self.address),
        )


def discover_lan_interfaces() -> tuple[LanInterface, ...]:
    if os.name != "nt":
        raise RuntimeError("LAN adapter discovery requires Windows")
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(  # noqa: S603 - static Windows inventory command
            [  # noqa: S607 - inbox Windows executable
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                _NETWORK_INVENTORY_SCRIPT,
            ],
            capture_output=True,
            check=False,
            timeout=15,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(
            "could not inspect Windows network adapters; confirm the Windows NetTCPIP "
            "module is available"
        ) from error
    if result.returncode != 0:
        raise RuntimeError(
            "could not inspect Windows network adapters; open Windows Settings and confirm "
            "the connected Ethernet or Wi-Fi network uses the Private profile"
        )
    if len(result.stdout) > _MAX_INVENTORY_BYTES:
        raise RuntimeError("Windows network adapter inventory exceeded its size limit")
    try:
        text = result.stdout.decode("utf-8-sig", errors="strict")
        raw = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Windows returned an invalid network adapter inventory") from error
    if not isinstance(raw, list):
        raise RuntimeError("Windows returned an invalid network adapter inventory")
    return _parse_inventory(raw)


def eligible_lan_interfaces(
    interfaces: Iterable[LanInterface],
) -> tuple[LanInterface, ...]:
    unique: dict[ipaddress.IPv4Address, LanInterface] = {}
    for interface in interfaces:
        if interface.eligibility_error is None:
            unique.setdefault(interface.address, interface)
    return tuple(sorted(unique.values(), key=lambda item: item.route_preference))


def select_lan_interface(
    interfaces: Iterable[LanInterface],
    requested_address: str | None = None,
) -> LanInterface:
    candidates = tuple(interfaces)
    eligible = eligible_lan_interfaces(candidates)
    if requested_address is not None:
        try:
            requested = ipaddress.IPv4Address(requested_address)
        except ipaddress.AddressValueError as error:
            raise RuntimeError("--lan-address must be a valid IPv4 address") from error
        matching = next((item for item in candidates if item.address == requested), None)
        if matching is None:
            raise RuntimeError(
                f"--lan-address {requested} is not assigned to a Windows network adapter"
            )
        reason = matching.eligibility_error
        if reason is not None:
            raise RuntimeError(f"--lan-address {requested} is not safe to advertise: {reason}")
        return matching
    if eligible:
        return eligible[0]
    visible = [
        f"{item.interface_alias} {item.address} ({item.eligibility_error})"
        for item in candidates
        if _is_rfc1918(item.address)
    ]
    detail = "; ".join(visible[:6]) or "no private IPv4 adapter was found"
    raise RuntimeError(
        "no active physical IPv4 adapter on a Windows Private network profile is available; "
        f"found: {detail}. Connect Ethernet or Wi-Fi to the trusted LAN and set its Windows "
        "network profile to Private"
    )


def _parse_inventory(raw: list[Any]) -> tuple[LanInterface, ...]:
    parsed: list[LanInterface] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"Windows network adapter inventory item {index} is invalid")
        try:
            address = ipaddress.IPv4Address(_required_string(item, "address"))
            gateway_text = _optional_string(item, "default_gateway")
            gateway = ipaddress.IPv4Address(gateway_text) if gateway_text else None
            prefix_length = _required_int(item, "prefix_length", minimum=0, maximum=32)
            interface_index = _required_int(item, "interface_index", minimum=1)
            interface_metric = _optional_int(item, "interface_metric", minimum=0)
            route_metric = _optional_int(item, "route_metric", minimum=0)
            parsed.append(
                LanInterface(
                    address=address,
                    prefix_length=prefix_length,
                    interface_index=interface_index,
                    interface_alias=_required_string(item, "interface_alias", maximum=256),
                    interface_description=_required_string(
                        item, "interface_description", maximum=512
                    ),
                    adapter_status=_required_string(item, "adapter_status", maximum=64),
                    hardware_interface=_required_bool(item, "hardware_interface"),
                    virtual=_required_bool(item, "virtual"),
                    network_category=_optional_string(item, "network_category", maximum=64),
                    default_gateway=gateway,
                    interface_metric=interface_metric,
                    route_metric=route_metric,
                )
            )
        except (ipaddress.AddressValueError, KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"Windows network adapter inventory item {index} is invalid"
            ) from error
    return tuple(parsed)


def _is_rfc1918(address: ipaddress.IPv4Address) -> bool:
    return any(address in network for network in _PRIVATE_NETWORKS)


def _required_string(item: Mapping[str, Any], key: str, *, maximum: int = 1_024) -> str:
    value = item[key]
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{key} must be a bounded non-empty string")
    return value


def _optional_string(item: Mapping[str, Any], key: str, *, maximum: int = 1_024) -> str | None:
    value = item[key]
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{key} must be a bounded string or null")
    return value or None


def _required_bool(item: Mapping[str, Any], key: str) -> bool:
    value = item[key]
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a boolean")
    return value


def _required_int(
    item: Mapping[str, Any], key: str, *, minimum: int, maximum: int = 2**31 - 1
) -> int:
    value = item[key]
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{key} must be an integer in range")
    return int(value)


def _optional_int(
    item: Mapping[str, Any], key: str, *, minimum: int, maximum: int = 2**31 - 1
) -> int | None:
    value = item[key]
    if value is None:
        return None
    return _required_int(item, key, minimum=minimum, maximum=maximum)
