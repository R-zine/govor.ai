# Mixed Ethernet/Wi-Fi LAN implementation and bounded check - 2026-10-25

## Scope

This maintenance change makes release address advertisement safe and deterministic when the
Windows host uses Ethernet and the Android phone uses Wi-Fi on one routable trusted private LAN.
It is an implementation/software record plus a real Windows adapter fail-closed check. It is not a
passing cross-interface phone/media benchmark because the active Ethernet profile was Public.

## Implementation

- `govor_launcher.network` queries the inbox Windows NetTCPIP module for each IPv4 address,
  physical/virtual state, connection status, network category, gateway, and route/interface metric.
- Eligibility requires active, physical, non-virtual, RFC1918, and Windows Private.
- Default selection follows an active default route and the lowest combined route/interface
  metric, then stable interface index/address ordering.
- `Start-Govor.cmd --lan-address <IPv4>` reaches the existing launcher parser and may select only
  another eligible local address.
- Selection occurs before TLS pairing state or the QR is created. Failure starts no LAN listener.
- Gateway binds and WebRTC gathering are unchanged. Router bridging/routing and Private-only
  Windows Firewall access remain deployment requirements.

ADR-0019 records why the app does not automatically change Windows network or firewall policy.

## Commands and results

| Command | Result |
| --- | --- |
| `uv run --cache-dir .cache/uv-lan --frozen pytest apps/launcher/tests/test_network.py apps/launcher/tests/test_cli.py apps/launcher/tests/test_pairing_qr.py -q` | Passed: 32 tests |
| `./scripts/test.ps1 -Scope python` | Passed after one mypy-only correction: 283 tests, 85.23% branch coverage, strict mypy, Ruff, and format checks |
| `./scripts/test.ps1 -Scope all` | Passed: Python plus 29 Kotlin, 9 C#, 21 real media tests, Godot import/build/self-test, and Android debug assembly |
| `uv run --cache-dir .cache/uv-lan --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-lan` | Passed with approved metadata access after the expected sandbox denial: no known vulnerabilities |
| `uv run --cache-dir .cache/uv-lan --frozen pre-commit run --all-files` with command-scoped safe-directory environment | Passed all hooks after approved initialization of pinned hook environments |
| Real `discover_lan_interfaces()` plus `select_lan_interface()` invocation | Correctly failed closed: active `Ethernet 3` `192.168.100.72` was physical but Public; disconnected physical Wi-Fi and virtual/link-local adapters were rejected |

The first Python-scope attempt stopped before tests because mypy identified an `Any` return from
the bounded inventory integer helper. Returning `int(value)` after the existing bool/type/range
guard resolved it; the complete scope then passed from the beginning.

The first repeat of pre-commit after the final documentation edit found an unreadable manifest in
the workspace-local hook cache. No source hook ran in that failed attempt. Initializing a fresh
workspace-local pinned hook cache and repeating the all-files command passed every hook.

## Current machine evidence

| Field | Value |
| --- | --- |
| Windows build | 10.0.26200 |
| Active adapter | `Ethernet 3` / Realtek PCIe GbE Family Controller |
| Address/prefix | `192.168.100.72/24` |
| Gateway | `192.168.100.1` |
| Physical / virtual | true / false |
| Windows network category | **Public** |
| Other physical adapter | `Wi-Fi 4`, disconnected (`192.168.100.78/24` stale inventory) |

No profile, firewall, router, or phone setting was modified. No gateway, renderer, media service,
or tone was started by this check.

## Acceptance boundary and next exact check

Software selection/filtering and launcher integration are verified. TCP 8765/8766, certificate-
pinned pairing/WSS, ICE, renderer video/application audio, and physical phone microphone return
over Ethernet-to-Wi-Fi are **blocked/not executed** while the active Ethernet network is Public.
The completed Milestone 9 Wi-Fi/Wi-Fi record cannot be relabeled as this topology.

The operator should deliberately set the intended Ethernet network to Private in Windows Settings,
allow only the Private firewall profile, then start the exact candidate and scan its new QR from a
physical phone on the intended non-isolated Wi-Fi. Verify control/media connection and microphone
return, then stop all services and record the exact package/device/router evidence. Guest/client
isolation or an unrouted VLAN must be fixed at the router; govor.ai does not bypass it.
