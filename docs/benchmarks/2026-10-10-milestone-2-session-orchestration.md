# 2026-10-10 Milestone 2 session-orchestration record

This is functional development evidence, not a hardware or performance benchmark. The Android
run used an emulator and loopback `adb reverse`; it does not satisfy any Milestone 9 physical phone,
Wi-Fi, codec-hardware, acoustic, target-machine performance, monitor-off, or soak requirement.

## Environment

- Date/time zone: 2026-10-10, Europe/Kiev.
- Windows process build: 10.0.26200.
- Renderer: Godot 4.7.2 stable .NET (`ed1daf0bf`), OpenGL compatibility renderer.
- GPU visible to the renderer: NVIDIA GeForce RTX 3060, driver 560.94.
- Android: Android Studio API 34 AVD `Pixel_3a_API_34_extension_level_7_x86_64`, serial
  `emulator-5554`.
- Transport: control on `127.0.0.1:8765`, media signaling on `127.0.0.1:8766`, both mapped to the
  emulator with `adb reverse`; WebRTC media remained DTLS-SRTP.
- Providers: `fake-scripted-stt`, `fake-scripted-dialogue`, and `fake-scripted-speech`; no model,
  credentials, cloud call, or production inference.

## Implemented path

1. Android opens the validated `/v1/control` WebSocket and requests a session.
2. The FastAPI host creates the domain state machine and dispatches allow-listed visual state to
   Godot's outbound loopback renderer connection.
3. Android plays a bounded 150 ms fake WAV and reports playback completion.
4. Hold-to-talk sends lifecycle events while real microphone frames travel on the existing WebRTC
   track.
5. The deterministic fake recognizer returns a scripted transcript from utterance metadata, the
   fake dialogue provider returns the next line, and the fake speech provider creates a second
   bounded WAV.
6. Android receives/plays the next teacher turn; Godot acknowledges all visual commands.
7. Cancel/disconnect stops tasks, resets Godot, clears the host registry, and closes both media and
   control connections.

The fake recognizer does not inspect or transcribe microphone samples. The test proves complete
application control flow plus independent microphone transport, not speech-recognition quality.

## Commands and results

| Command/check | Result | Evidence and limit |
| --- | --- | --- |
| `./scripts/test.ps1 -Scope python` | passed during implementation | Strict Ruff/mypy; complete turn, invalid messages, provider failure, timeout, cancellation, dual WebSockets, logging redaction, and repeated-session tests |
| `./scripts/test.ps1 -Scope contracts` | passed | 12 JSON Schema/shared-fixture tests |
| `./scripts/test.ps1 -Scope kotlin` | passed after one fixture assertion correction | 9 JVM tests, including strict shared-fixture decoding and every declared transition |
| `./scripts/test.ps1 -Scope csharp` | passed | 5 strict contract/allow-list tests using the shared renderer fixture |
| `./scripts/test.ps1 -Scope godot` | passed | Headless import, successful C# build, and renderer contract self-test marker; the final offline run emitted the recorded NuGet audit and Windows certificate-store environment warnings |
| `./scripts/test.ps1 -Scope all` | passed in the final handoff run | 46 Python tests at 87.95% branch coverage, 12 contract tests, 9 Kotlin tests, 5 C# tests, 10 real aiortc media tests, Godot import/build/self-test, and Android APK assembly |
| `./scripts/build.ps1 -Target renderer` | passed after one harness correction | Export succeeded; only the exact known Godot Windows root-certificate-store startup warning is ignored, while all other `ERROR:` lines remain fatal |
| `./scripts/renderer-smoke.ps1` | passed | Final run observed 5 changing non-black frames and 7 non-silent PCM blocks; peak 2621; bounded clean exit |
| `./scripts/emulator-renderer-smoke.ps1` | passed on the final run | Complete fake turn, renderer-unavailable retry, all renderer actions, 1280x720 video, application PCM, microphone return, disconnect/reconnect, completed-turn UI artifact, and cleanup |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-m2-final` | passed | No known vulnerabilities found |

## Failures found and corrected

- The first Kotlin shared-fixture run failed one assertion because the test expected `Welcome`
  while the canonical fixture contains the full predetermined sentence. The assertion was corrected;
  all 9 tests then passed.
- The first renderer export was reported as failed by the wrapper even though Godot produced the
  executable. Godot 4.7.2 emitted `Failed to read the root certificate store` while offline. The
  wrapper now excludes only that exact known line and continues to reject every other error; the
  repeat export passed.
- The first combined emulator script polled successful health responses without yielding between
  attempts, exhausting its renderer-connect loop before Godot connected. Cleanup removed both
  servers, the renderer, the Android app, and reverse mappings. A bounded 100 ms yield and an
  explicit renderer runtime log were added; the repeat run passed.
- The local renderer smoke initially treated the same known certificate-store line and Godot's
  inaccessible default user log location as runtime failures. Passing an explicit repository-local
  log path removed the user-log error, and the exact certificate warning is filtered as above.

## Emulator evidence

- Android UI reached `media: connected · lesson: awaiting learner` after initial teacher playback.
- The complete turn check observed the scripted transcript `I would like coffee, please.` and the
  next teacher sentence `Thank you. Would you like coffee or tea?` before taking the screenshot.
- Godot logged acknowledgements for `session_started`, `teacher_speaking`, `awaiting_learner`,
  `recording`, `processing`, and `reset` across two sessions.
- aiortc logged non-black 1280x720 renderer frames, one bounded 48 kHz application-audio source,
  and 48 kHz/960-sample microphone frames before and after reconnect.
- Android libwebrtc reported 120 received/rendered frames, zero dropped, over 4.002 seconds
  (30.0 fps). This short loopback interval is diagnostic evidence, not a performance result.
- The script's `finally` block stopped the Android app, renderer, both servers, and both `adb
  reverse` mappings. Follow-up checks found no listeners on 8765/8766 and no renderer process.
- The control log recorded event names plus correlation/session identifiers and contained no
  learner transcript text or raw audio.

Final artifacts:

- `apps/android/app/build/outputs/apk/debug/app-debug.apk`: 58,656,824 bytes, SHA-256
  `eef822f1ddca3ed4338163936c0b71acd1134f0cefe0efa82d2e258d48730b79`.
- `apps/renderer/Builds/Windows/GovorRenderer.exe`: 109,372,928 bytes, SHA-256
  `65d86d986f0f5508a2dede1bce653bfb21fc6fd8cf06aed43872c0806e679175`.

Ignored runtime artifacts:

- `.cache/godot-emulator-control.*.log`
- `.cache/godot-emulator-renderer.*.log`
- `.cache/godot-emulator-server.*.log`
- `.cache/godot-emulator-window.xml`
- `.cache/godot-emulator-completed-turn.xml`
- `.cache/godot-emulator-connected.png`
- `.cache/godot-emulator-webrtc.log`

## Acceptance interpretation

Milestone 2's deterministic application skeleton is verified. It is safe to begin Milestone 3.
No real AI capability, physical device behavior, Wi-Fi behavior, acoustic quality, codec hardware,
latency/resource target, monitor-off behavior, or stability duration is claimed here. All such
release evidence remains mandatory in Milestone 9.
