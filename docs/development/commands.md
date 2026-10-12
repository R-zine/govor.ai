# Development commands

| Command | Purpose |
| --- | --- |
| `./scripts/bootstrap.ps1` | Install/validate pinned development dependencies |
| `./scripts/bootstrap.ps1 -IncludeMedia` | Also resolve Milestone 1 WebRTC experiment packages |
| `./scripts/bootstrap.ps1 -IncludeRenderer` | Install pinned Godot .NET editor and export templates |
| `./scripts/dev.ps1 -Mode mock` | Run loopback-only deterministic fake host |
| `./scripts/test.ps1 -Scope python` | Python lint, format, type, unit/integration, coverage |
| `./scripts/test.ps1 -Scope contracts` | JSON Schema and fixture tests |
| `./scripts/test.ps1 -Scope kotlin` | Kotlin/JVM core unit tests |
| `./scripts/test.ps1 -Scope csharp` | Pure C# contract tests |
| `./scripts/test.ps1 -Scope media` | Real in-process WebRTC negotiation and bidirectional media tests |
| `./scripts/test.ps1 -Scope godot` | Godot headless import, C# build, and renderer self-test |
| `./scripts/test.ps1 -Scope all` | All tests, Godot validation, and debug APK build |
| `./scripts/test.ps1 -Scope hardware` | Milestone 9 physical-device release suite; never a mock or emulator substitute |
| `./scripts/build.ps1` | Build Android debug and C# development artifacts |
| `./scripts/build.ps1 -Target renderer` | Export the local Godot Windows renderer |
| `./scripts/renderer-smoke.ps1` | Run a muted, bounded Godot frame/PCM/cleanup smoke check |
| `./scripts/renderer-scene-smoke.ps1` | Capture and measure all four validated scenes plus avatar/software encoding |
| `./scripts/emulator-renderer-smoke.ps1` | Development-only Godot/aiortc/native-emulator media and microphone check |
| `./scripts/benchmark.ps1 -Profile inventory` | Write environment inventory, not performance results |
| `./scripts/benchmark.ps1 -Profile renderer` | Measure scene/avatar/render/software-encode work concurrently with Qwen3 4B |
| `./scripts/progress.ps1 -Action View` | View local structured learner progress/settings as JSON |
| `./scripts/progress.ps1 -Action Export -OutputPath <path>` | Export structured progress; never audio/transcripts |
| `./scripts/progress.ps1 -Action Delete -ConfirmDelete` | Delete progress history while preserving settings |

For pre-release development only, the feasibility media server can be exposed to a physical phone
on a trusted LAN:

```powershell
./scripts/media-dev.ps1 -PairingToken '<at-least-32-random-characters>' -AllowInsecureDevLan
```

Use the Windows host's LAN IP, port `8766`, and the same token in the debug Android app. This
deliberately uses cleartext signaling and is development-only. It cannot satisfy Milestone 9
physical-network acceptance, which requires WSS and real pairing. WebRTC media itself uses
DTLS-SRTP.

Release packaging and media hardware benchmarks intentionally fail with an explicit explanation
until their milestone implementations exist.

For Android Studio emulator development, run `adb reverse tcp:8766 tcp:8766`, keep the media
server on loopback, and connect the debug app to its default `127.0.0.1:8766`. Stop the server as
soon as the audio check is finished. Emulator results complete the Milestone 1 architecture proof
but never count as Milestone 9 physical-device acceptance.

After building and launching the Godot player, replace the diagnostic source with the local
renderer bridge by adding `-Source Renderer` to `media-dev.ps1`. Keep `-BindHost 127.0.0.1` when
using `adb reverse`. This source currently requires Windows; it does not make the signaling path
release-safe. Build success alone does not prove live viewport/audio delivery.
