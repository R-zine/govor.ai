# Mixed Ethernet/Wi-Fi LAN implementation and bounded check - 2026-10-25

## Scope

This maintenance change makes release address advertisement safe and deterministic when the
Windows host uses Ethernet and the Android phone uses Wi-Fi on one routable trusted private LAN.
It is an implementation/software record plus real Windows adapter-selection checks. It is not a
passing cross-interface phone/media benchmark because no Android device was available for the
corrected 2026-10-26 run.

## Implementation

- `govor_launcher.network` queries the inbox Windows NetTCPIP module for each IPv4 address,
  physical/virtual state, connection status, network category, gateway, and route/interface metric.
- Eligibility requires active, physical, non-virtual, RFC1918, and a recognized Windows network
  category. Private is preferred; Public is accepted with a trusted-router/firewall/no-port-
  forwarding warning because the Windows label does not determine IP address scope.
- Default selection prefers Private, then follows an active default route and the lowest combined
  route/interface metric, followed by stable interface index/address ordering.
- `Start-Govor.cmd --lan-address <IPv4>` reaches the existing launcher parser and may select only
  another eligible local address.
- Selection occurs before TLS pairing state or the QR is created. Failure starts no LAN listener.
- Gateway binds and WebRTC gathering are unchanged. Router bridging/routing and a Windows Firewall
  allowance matching the selected profile/local network remain deployment requirements.

ADR-0019 records the correction and why the app does not automatically change Windows network or
firewall policy.

## Commands and results

| Command | Result |
| --- | --- |
| `uv run --cache-dir .cache/uv-lan --frozen pytest apps/launcher/tests/test_network.py apps/launcher/tests/test_cli.py apps/launcher/tests/test_pairing_qr.py -q` | Passed: 32 tests |
| `./scripts/test.ps1 -Scope python` | Passed after one mypy-only correction: 283 tests, 85.23% branch coverage, strict mypy, Ruff, and format checks |
| `./scripts/test.ps1 -Scope all` | Passed: Python plus 29 Kotlin, 9 C#, 21 real media tests, Godot import/build/self-test, and Android debug assembly |
| `uv run --cache-dir .cache/uv-lan --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-lan` | Passed with approved metadata access after the expected sandbox denial: no known vulnerabilities |
| `uv run --cache-dir .cache/uv-lan --frozen pre-commit run --all-files` with command-scoped safe-directory environment | Passed all hooks after approved initialization of pinned hook environments |
| Real `discover_lan_interfaces()` plus `select_lan_interface()` invocation | Correctly failed closed: active `Ethernet 3` `192.168.100.72` was physical but Public; disconnected physical Wi-Fi and virtual/link-local adapters were rejected |
| Corrected focused launcher tests on 2026-10-26 | Passed: 34 tests, including Private preference and Public-category RFC1918 selection/warning marker |
| Corrected `./scripts/test.ps1 -Scope python` | Passed: Ruff/format/mypy, 285 tests, 85.20% branch coverage |
| Corrected real selector invocation on 2026-10-26 | Selected `192.168.100.72 Ethernet 3 Public` and returned `uses_public_profile=True` |
| Elevated `adb devices -l` on 2026-10-26 | ADB daemon started; no physical phone or emulator was listed |
| Read-only Windows Firewall inventory | Public and Private profiles enabled; old package-specific Python allowances exist but no rule was changed and a new versioned runtime path may prompt again |
| `./scripts/package.ps1 -Version '0.1.17' -VersionCode 18 -GradleUserHome '.cache/gradle' -GradleOffline -NoArchive` | Passed after releasing a stale Gradle daemon file lock: Godot export, Android release lint/build, v2 signing, embedded-runtime import, corresponding-source, and prerequisite checks |
| Packaged `0.1.17` selector invocation | Selected `192.168.100.72 Ethernet 3 Public`; `uses_public_profile=True` |
| Corrected final `./scripts/test.ps1 -Scope all` | Passed: 285 Python tests at 85.20% branch coverage, 29 Kotlin tests, 9 C# tests, 21 real media tests, Godot import/build/self-test, and Android debug assembly |
| Corrected final frozen media/speech dependency audit | Passed: no known vulnerabilities |
| Corrected all-files pre-commit gate | Passed JSON/YAML, EOF/line-ending/whitespace, private-key/large-file, Ruff check/format, contracts, PowerShell syntax, and affected-application tests |

The first Python-scope attempt stopped before tests because mypy identified an `Any` return from
the bounded inventory integer helper. Returning `int(value)` after the existing bool/type/range
guard resolved it; the complete scope then passed from the beginning.

The first repeat of pre-commit after the final documentation edit found an unreadable manifest in
the workspace-local hook cache. No source hook ran in that failed attempt. Initializing a fresh
workspace-local pinned hook cache and repeating the all-files command passed every hook.

The first `0.1.17` packaging attempt produced the renderer but the headless Godot process did not
exit and was interrupted; that partial stage was not accepted. A later attempt reached Android and
failed on an access-denied, locked Gradle transform JAR. Stopping the project Gradle daemon released
the stale lock. The complete offline package command then passed from Godot export through all
release checks without deleting cache or source data.

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
| Corrected portable candidate | `govor.ai-0.1.17-windows-x64` |
| Signed Android companion | `0.1.17`, version code 18, APK Signature Scheme v2 |
| APK size / SHA-256 | 59,891,893 bytes / `cd7ac297a79871b5c75564168265b0b0e574a6ad12494968335ec659b77bb478` |

No profile, firewall, router, or phone setting was modified. No gateway, renderer, media service,
or tone was started by these selection checks.

Historical firewall rules for old package paths include broad `RemoteAddress=Any` entries on their
respective profiles. The correction does not create or broaden such rules. Because each portable
version has a new embedded-Python path, the exact next candidate must receive its own deliberate
allowance if Windows prompts; the operator should select only the profile belonging to this trusted
router and must not add router port forwarding.

## Acceptance boundary and next exact check

Software selection/filtering and launcher integration are verified. The original Public-profile
rejection was a design error: Windows' category is firewall/discovery metadata, while
`192.168.100.72/24` remains local to the router. The amended implementation permits that address
with a warning and retains the other safety filters.

TCP 8765/8766, certificate-pinned pairing/WSS, ICE, renderer video/application audio, and physical
phone microphone return over Ethernet-to-Wi-Fi are still **blocked/not executed** because ADB found
no attached Android device. The completed Milestone 9 Wi-Fi/Wi-Fi record cannot be relabeled as
this topology.

Attach the physical phone on the intended non-isolated Wi-Fi, allow the exact packaged runtime in
Windows Firewall for the selected trusted-router profile/local network, then start the exact
candidate and scan its new QR. Verify control/media connection and microphone return, stop all
services, and record the exact package/device/router evidence. Never add router port forwarding.
Guest/client isolation or an unrouted VLAN must be fixed at the router; govor.ai does not bypass
it.
