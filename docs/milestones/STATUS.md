# Current verified status

Last updated: 2026-10-10

## Outcome

Milestone 0 is complete. The pinned Python, Kotlin/Gradle, C#, Android, media, and repository
quality gates pass from the source checkout.

Milestone 1 is complete on the master specification's revised native-emulator development gate.
The native Android client and aiortc gateway work on an Android Studio API 34 emulator, including
video, application audio, hold-to-talk microphone return, and disconnect/reconnect with both
diagnostic and Godot sources. ADR-0004 moves the complete physical phone/Wi-Fi/target-hardware
acceptance bundle to Milestone 9; none of that hardware behavior is inferred from this result.

Milestone 2 is complete. The host-owned control plane now runs a fully validated deterministic
turn across the FastAPI host, native Android client, and Godot renderer. It includes strict shared
contracts, cancellation, retry, explicit deadlines, recoverable failures, correlated redacted
logging, and bounded cleanup. Milestone 3 may begin. The scripted fake providers do not prove real
speech recognition, dialogue quality, or speech synthesis.

ADR-0003 now selects Godot 4.7.2 .NET as the only renderer. The earlier proof from the proprietary
engine was removed completely, including source, project metadata, build scripts, and dependencies.
Godot import, C# compilation, self-test, Windows export, local runtime, non-black shared-memory
video, non-silent application PCM, and emulator delivery have all executed successfully. The
current synchronous `SubViewport.GetTexture().GetImage()` readback is accepted for continued
development. It may still require revision if the mandatory Milestone 9 target-hardware
measurements fail.

## Current implementation

- `apps/renderer` is a Godot 4.7.2 .NET project with an animated cyan placeholder, lit 3D scene,
  dedicated 1280x720 `SubViewport`, and a two-second 48 kHz mono application tone.
- The tone stops automatically. Runtime smokes are muted by default; the single supervised
  audible check also stopped after two seconds.
- Godot publishes top-to-bottom RGBA into a latest-frame Windows named mapping and PCM into a
  bounded 64-block ring. The mappings are process-local and expose no LAN listener.
- aiortc owns signaling, encoding, transport, pacing, and silence fallback. The Android wire
  contract did not change during the renderer migration.
- Bootstrap downloads the exact Godot .NET editor and export templates to ignored repository-local
  directories and verifies pinned SHA-512 digests. No account or license activation is required.
- `scripts/test.ps1 -Scope godot` imports the project, builds C# successfully, and requires the
  `GOVOR_GODOT_SELF_TEST_PASS` marker.
- `scripts/build.ps1 -Target renderer` exports the Windows player and rejects missing artifacts or
  Godot export errors.
- `scripts/renderer-smoke.ps1` requires changing non-black frames, non-silent PCM, the proof image,
  the bounded tone completion marker, an empty runtime error log, and clean exit.
- `scripts/emulator-renderer-smoke.ps1` uses a fresh unlogged token, loopback signaling through
  `adb reverse`, the exported Godot player, native Android/libwebrtc, and hold-to-talk microphone.
  Cleanup stops the app, renderer, both servers, and both reverse mappings.
- The hardware harness deliberately ignores serials beginning with `emulator-`.
- Release cleartext remains disabled; only the debug manifest enables the feasibility connection.
- A closed version 1 control schema and strict Python, Kotlin, and C# bindings reject unknown
  message types, fields, malformed identifiers, and invalid timing at process boundaries.
- The framework-independent domain state machine is host-owned. FastAPI orchestrates cancellable
  provider tasks, renderer acknowledgements, playback/recording/provider deadlines, retry, error
  propagation, and a zero-retention session registry.
- The fake providers are explicitly named and report explicit capabilities. Fake STT consumes only
  a bounded media reference and duration; it does not inspect or transcribe microphone samples.
- Android owns bounded WAV playback and the real WebRTC push-to-talk microphone lifecycle. Godot
  connects outbound to a loopback-only control endpoint and accepts only six visual actions.
- The emulator smoke deliberately exercises renderer-unavailable recovery before completing a
  teacher/learner/teacher turn, media reconnect, renderer reset, and process/network cleanup.

## Verification ledger

| Command or check | Result | Evidence and limits |
| --- | --- | --- |
| `./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -NoDownload` | verified passing | Pinned local Python/.NET/Godot assets and locked dependencies restored without a download |
| `./scripts/test.ps1 -Scope all` | verified passing | 2026-10-10 final run; Python, contracts, Kotlin, C#, media, Godot, and Android APK build |
| Python gate | verified passing | Ruff check/format, strict mypy, 46 tests, 87.95% branch coverage |
| Contract schema gate | verified passing | 12 valid/invalid version 1 schema and shared-fixture tests |
| Kotlin gate | verified passing | 9 JVM contract/state-machine tests |
| Pure C# gate | verified passing | 5 .NET contract/allow-list tests |
| Media gate | verified passing | Strict mypy and 10 tests, including real aiortc loopback, renderer-buffer validation, and clean remote-track teardown |
| Godot gate | verified passing | Headless import, successful C# build, and self-test marker; offline NuGet vulnerability lookup and Windows certificate-store warnings are recorded below |
| `./scripts/build.ps1 -Target renderer` | verified passing | 109,372,928-byte Windows export; SHA-256 `65d86d986f0f5508a2dede1bce653bfb21fc6fd8cf06aed43872c0806e679175` |
| `./scripts/renderer-smoke.ps1` | verified passing | Final run: 5 complete/changing frames, RGB maximum 255, 7 PCM blocks, peak 2621; proof PNG and clean bounded exit |
| Supervised audible renderer smoke | verified passing | Brief PC check only; tone completion marker at two seconds and process stopped |
| `./scripts/emulator-renderer-smoke.ps1` | verified passing with limits | Complete fake turn and recovery path; aiortc received non-black 1280x720 Godot RGBA (`rgb_max=255`) and 48 kHz PCM (`peak=2621`); Android reported 120 received/rendered frames, zero drops, over 4.002 seconds (30.0 fps); video and 48 kHz/960-sample microphone return passed again after reconnect |
| Godot emulator screenshot | inconclusive | UI/status captured, but the WebRTC `SurfaceView` area is black in ADB screencaps; transport logs prove non-black input and Android render callbacks, not a screenshot of scene pixels |
| Renderer-source reconnect/teardown | verified passing on emulator | Second peer received non-black Godot video and microphone frames; no unobserved task exception and no retained tone block replay |
| Milestone 1 development architecture gate | complete | ADR-0002/0003 confirmed on native-emulator evidence; ADR-0004 defers all physical target-environment acceptance to Milestone 9 |
| Android APK build | verified passing | 58,656,824 bytes; SHA-256 `eef822f1ddca3ed4338163936c0b71acd1134f0cefe0efa82d2e258d48730b79` |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-m2-final` | verified passing | Final Milestone 2 audit: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| Pre-commit across all tracked/untracked sources | verified passing | JSON/YAML, line endings/whitespace, secret/size checks, Ruff, and contract tests; first pass normalized generated line endings, second pass clean |
| `./scripts/hardware-test.ps1` | Milestone 9 not executed | Ignores the active emulator and exits 2 because no physical phone is connected; this does not reopen Milestone 1 |
| Physical Android/Wi-Fi/media/soak bundle | Milestone 9 not executed | No suitable physical phone; mandatory before release, not a prerequisite for Milestones 2-8 |
| Remote GitHub Actions | not executed | Workflow includes the Godot renderer job, but the current milestone snapshot has not run remotely |

The final `./scripts/test.ps1 -Scope all` run passed on 2026-10-10: 46 Python tests at 87.95%
branch coverage, 12 contract-schema tests, 9 Kotlin tests, 5 pure C# tests, 10 media tests, Godot
import/build/self-test, and the Android debug APK build. Pytest emitted the existing Starlette
`httpx` deprecation warning. Offline NuGet vulnerability lookup produced `NU1900`, Godot could not
read the Windows root-certificate store, Android analytics could not write outside the workspace,
and the Kotlin daemon could not write its user-profile marker before Gradle successfully used its
documented in-process fallback. These were environment warnings; every gate completed successfully.

## Renderer evidence and limitations

The local proof image visibly contains the cyan animated placeholder, ground, lighting, and
background. The live bridge probe observed multiple changing frames and explicitly rejected an
all-black stream. In the emulator run, the aiortc peer logged `rgb_min=0 rgb_max=255`, Android
libwebrtc logged `Reporting first rendered frame` and a 1280x720 resolution change, application
PCM reached the first peer, and microphone frames returned to Windows before and after reconnect.
After the two-second tone ended, the second peer correctly received silence rather than a retained
PCM block. The final emulator render interval reported 120 frames in 4.002 seconds (30.0 fps), with
zero dropped frames; this short loopback sample is development evidence, not a hardware benchmark.

The ADB screenshot still shows a black video region. Because the local proof image is non-black,
the peer received non-black pixels, and Android emitted render callbacks, this is consistent with
an ADB/`SurfaceView` capture limitation, but that explanation has not been independently proven.
No screenshot-based scene-visibility claim is made.

No controlled cadence distribution, latency, CPU, GPU, RAM, VRAM, thermals, Wi-Fi, hardware
encoder/decoder, monitor-off, background/foreground, physical audio, or 30-minute soak result
exists. The emulator used the virtual `c2.goldfish.vp8.decoder`, which is not hardware-decoder
evidence. Every one of these checks remains mandatory in Milestone 9.

Detailed migration evidence is in `docs/benchmarks/2026-10-09-godot-renderer-migration.md`.

## Environment and artifacts

- Windows process build 10.0.26200.
- NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94.
- Godot 4.7.2 stable .NET (`ed1daf0bf`), repository-local editor and export templates.
- Android Studio API 34 AVD `Pixel_3a_API_34_extension_level_7_x86_64`, serial
  `emulator-5554`, used only for development evidence.
- Renderer: `apps/renderer/Builds/Windows/GovorRenderer.exe` (ignored build output).
- Debug APK: `apps/android/app/build/outputs/apk/debug/app-debug.apk`.
- Runtime logs/proof images: ignored files under `.cache/`.
- Inventory: `docs/benchmarks/local/latest-inventory.json` (inventory only, no performance claim).

## Next steps

Milestone 3 is now the next eligible implementation milestone:

1. Define production local provider interfaces and capability discovery without coupling the
   domain to a model runtime.
2. Integrate and verify real local English, Bulgarian, and mixed-language STT/dialogue paths while
   retaining deterministic fakes for tests.
3. Record real microphone transcription accuracy, latency, memory, error handling, and offline
   behavior without representing unavailable timing metadata as measured data.

Deferred mandatory Milestone 9 work:

1. Connect a physical Android phone over the intended Wi-Fi path and execute video, audible
   application audio, microphone return, lifecycle, interruption, reconnect, and teardown checks.
2. Validate pairing/WSS/firewall behavior and hardware codec selection/fallback.
3. Measure cadence, latency, packet loss, CPU/GPU/RAM/VRAM, thermals, acoustics, orientation,
   unfocused/monitor-off behavior, and a 30-minute soak.
4. Retain or replace synchronous readback using those measurements; use a Godot GDExtension or
   native capture/hardware-encoding bridge if necessary.

Milestone 1 must not be reopened merely because Milestone 9 hardware is unavailable. Conversely,
Milestone 9 must not pass using emulator evidence.

## Exact resume commands

```powershell
git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' status --short --branch
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -NoDownload
./scripts/test.ps1 -Scope all
./scripts/build.ps1 -Target renderer
./scripts/renderer-smoke.ps1
./scripts/emulator-renderer-smoke.ps1
./scripts/dev.ps1 -Mode mock
```
