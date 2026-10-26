# QR-first release pairing verification — 2026-10-25

## Scope and evidence boundary

This is post-Milestone 9 maintenance evidence for the new pairing bootstrap and UI. It verifies
contract generation/validation, Segno/ZXing compatibility, Godot overlay startup, signed Android
release presentation, camera permission/scanner startup, packaging, and software regression gates.
It does not replace the 2026-10-22 physical Milestone 9 acceptance candidate.

No physical Android device was attached when the final feature candidate was ready (`adb devices
-l` returned no devices). The API 34 emulator evidence below therefore does **not** prove a real
camera can focus on/read the host display. That physical-camera scan is not executed and remains a
recommended regression check before distributing this maintenance release.

## Machine and fixtures

- Windows process build 10.0.26200, Europe/Kiev time zone.
- NVIDIA GeForce RTX 3060, driver 560.94.
- Godot 4.7.2 stable .NET (`ed1daf0bf`).
- Android Studio API 34 AVD `Pixel_3a_API_34_extension_level_7_x86_64`, `emulator-5554`, audio
  disabled; used only for software/UI evidence.
- Signed candidate: `0.1.15`, Android version code 16, existing release signer SHA-256
  `b7022cb8bbcc0a4828cf73e5ef958e1b431ccce697020577c4a502a66ec59843`.

## Implementation checked

- The launcher builds a compact `pairing.bootstrap` version 1 envelope with the selected control
  and media endpoints, eight-digit one-time code, uppercase certificate SHA-256, and Unix expiry.
  Pinned Segno 1.6.6 writes it atomically below the protected per-user security directory.
- Only the PNG path enters the Godot command line. The host-only overlay is outside the captured
  `SubViewport`, covers the scene until `session_started`, and the launcher removes the image on
  shutdown.
- Android uses pinned ZXing Android Embedded 4.3.0. Its strict local decoder rejects oversized,
  expired, unknown-field/version/message, and malformed bootstrap input before networking. A
  valid QR enters the existing certificate-pinned HTTPS pairing exchange.
- A first-run release shows **Scan host QR** as the primary action. **Pair manually** is collapsed
  and retains every previous diagnostic field. Stored credentials offer one-tap reconnect, and
  the saved-host state updates immediately after a fresh pairing.

## Commands and results

| Command/check | Result |
| --- | --- |
| `uv run --cache-dir .cache/uv-qr --frozen pytest apps/launcher/tests/test_pairing_qr.py apps/launcher/tests/test_cli.py tests/contracts/test_json_schemas.py -q` | passed: 55 tests |
| `./scripts/test.ps1 -Scope kotlin` | passed: 29 JVM tests; includes strict bootstrap tests and one exact Segno-module-to-ZXing decode |
| `./scripts/test.ps1 -Scope godot` | passed: import, C# build, headless self-test |
| `./scripts/build.ps1 -Target renderer` | passed: Windows export contains `PairingQrOverlay.cs` |
| bounded exported-player launch with generated QR, `--mute-local-audio --exit-after-tone` | exit 0; scene applied, QR image loaded without runtime error, two-second fixture completed muted, player stopped |
| `./scripts/build.ps1 -Target android` | passed: API 34 debug assembly with scanner dependency |
| signed release on API 34 emulator | primary QR action visible; manual fields absent until expanded; camera permission appeared in context; `com.journeyapps.barcodescanner.CaptureActivity` opened with the expected local prompt and no fatal exception |
| `./scripts/test.ps1 -Scope all` | passed: Ruff/format/mypy; 268 Python tests at 85.18% branch coverage; 29 Kotlin, 9 C#, 21 real-media tests; Godot import/build/self-test; Android debug APK |
| `uv run --cache-dir .cache/uv-qr --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-qr-pairing` | passed: no known vulnerabilities |
| `./scripts/package.ps1 -Version '0.1.15' -VersionCode 16 -GradleUserHome '<repo>/.cache/gradle' -GradleOffline -NoArchive` | passed: Godot export, signed APK/lint/signature verification, embedded runtime with Segno, source/notices, imports, prerequisites, packaged wrapper doctors |
| `uv run --cache-dir .cache/uv-qr --frozen pre-commit run --all-files` | passed: JSON/YAML, EOF/line endings/whitespace, private-key/large-file checks, Ruff, contracts, PowerShell syntax, and affected-application tests |

The final signed APK is 59,891,893 bytes with SHA-256
`a01f9dea01bba8600ced9f5a9085c3991823e22cc9de34a8c0c370b441e52d63`. It reports
`versionName=0.1.15`, `versionCode=16`, min SDK 26, target/compile SDK 34, and retains APK Signature
Scheme v2 with the established signer.

## Mixed Ethernet/Wi-Fi assessment (not implemented in this QR change)

No transport or contract rewrite is required for a wired Windows host and Wi-Fi phone on the same
routable trusted private LAN: the gateways already bind all IPv4 interfaces and WebRTC gathers
interface candidates. The unresolved part is deterministic address/interface selection on a
multi-homed PC. The current launcher advertises one sorted hostname-resolved IPv4 address, which
may be a VPN, virtual, isolated, disconnected, or Public-profile interface.

The follow-up should enumerate active physical adapters and Windows network categories, exclude
unsafe candidates, choose or let the user choose a reachable private address, keep firewall scope
on the trusted local network, and test TCP 8765/8766 plus ICE across the Ethernet-to-access-point path. Router
client isolation and VLAN routing must remain explicit failure modes. This assessment makes no
mixed-topology acceptance claim.

The subsequent ADR-0019 maintenance change implements deterministic physical RFC1918 adapter
selection and a bounded override. Its 2026-10-26 amendment correctly treats Windows Public as a
firewall/discovery category rather than internet address scope. The dated LAN benchmark retains the
still-pending physical Ethernet-to-Wi-Fi evidence boundary.

## Cleanup and limitations

The QR overlay smoke exited itself with local audio muted. No host/media service was started for
the emulator UI-only check. The emulator app was force-replaced with the signed candidate and its
test-only app state cleared. No physical-phone installation or real camera scan was executed.
