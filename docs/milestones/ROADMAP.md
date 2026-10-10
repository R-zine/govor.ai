# Product roadmap

Status legend: `in progress`, `blocked`, `not started`, `complete` (only when every acceptance
criterion has direct evidence).

| Milestone | Status | Depends on | Acceptance summary |
| --- | --- | --- | --- |
| 0. Repository foundation | complete | Master specification | Source-only bootstrap and full suite pass; contracts, pre-commit, CI syntax, mock mode, and pinned/locked dependencies verified |
| 1. Native streaming proof | complete | M0 foundation | Native emulator diagnostic and Godot media, microphone return, reconnect, cleanup, and development architecture decision pass |
| 2. Session orchestration | complete | M1 architecture decision (satisfied) | Complete validated fake turn cycle across host/Android/renderer; cancellation/timeouts/errors; leak-free repeated sessions |
| 3. Local AI/bilingual | not started | M2 contracts/orchestration | Local LLM/STT, English/Bulgarian/mixed intents, valid structured output, real microphone transcription, measured latency/memory |
| 4. Speech/phonemes | not started | M3 providers | English/Bulgarian TTS/fallback, speed/replay, IPA, real alignment/fallback, synchronized subtitles/word replay |
| 5. Teaching/progress | not started | M3-4 | Four complete guided scenarios, adaptive explainable teaching, questions do not break lessons, SQLite persistence/resume |
| 6. Avatar/scenes | not started | M1 media decision, M4 timing | Avatar and four validated dynamic environments, lip sync/fallback, memory/performance evidence |
| 7. Optional cloud/privacy | not started | Stable provider interfaces | Independent opt-in providers, offline default, OS secret storage, no unintended cloud/secret logging |
| 8. Packaging/distribution | not started | M1-7 | Clean Windows install/launcher, signed stable APK/update, integrity-checked models, no dev tools, clean shutdown |
| 9. Release acceptance and target hardware | not started | M8 | Physical phone/Wi-Fi/audio/codecs/lifecycle/performance/monitor-off/soak bundle, full automated/manual/security suite, and complete local-first cafe scenario |

## Critical path

M0 reproducibility -> M1 Godot-to-native-emulator media proof and development architecture
decision -> M2 control skeleton -> M3 real local AI -> speech -> teaching/scenes ->
privacy/provider options -> packaging -> M9 physical target-hardware and release acceptance.

Milestone 1 is complete. Its emulator evidence does not satisfy or reduce the mandatory Milestone 9
physical target-hardware bundle.

## Milestone 2 acceptance tracking

Verified software and native-emulator evidence:

- Closed version 1 session-control schema plus strict Python, Kotlin, and C# bindings and shared
  cross-language fixtures.
- Host-owned domain transitions, FastAPI orchestration, correlation-safe logging, explicit fake
  provider capabilities, renderer acknowledgements, provider/renderer/playback/recording timeouts,
  cancellation, retry, error propagation, and cleanup.
- Native Android control client with state display, bounded fake WAV playback, playback completion,
  push-to-talk lifecycle events, transcript/teacher-turn display, retry, cancellation, and strict
  response validation.
- Godot loopback control client with a closed visual-action set and command acknowledgements.
- Complete scripted turn on the API 34 emulator: initial teacher audio, hold-to-talk microphone
  return, fake STT transcript, fake dialogue reply, fake speech audio, next teacher turn, renderer
  state changes, disconnect/reconnect, and clean teardown.
- Injected provider/renderer failures are recoverable; invalid and out-of-order messages are safely
  rejected; every domain transition is tested; 20 repeated sessions leave zero registry entries.

Milestone 2 is complete. Milestone 3 may begin. The fake recognizer does not transcribe media and
the generated tones are not production speech evidence. Emulator execution remains development
evidence only and does not satisfy any Milestone 9 physical target-hardware criterion.

## Milestone 0 acceptance tracking

- Fresh source bootstrap: **verified passing** on 2026-10-08 in an isolated, source-only
  temporary workspace with cold Python/.NET resolution.
- Python unit tests: **verified passing**, 17 tests, 94.51% branch coverage.
- Kotlin unit tests: **verified passing**, 3 tests.
- Pure C# tests: **verified passing**, 2 tests.
- Contract validation and pre-commit hooks: **verified passing**.
- CI configuration: **verified locally**; remote GitHub Actions has not executed.
- Model/credential-free mock: **verified passing** on loopback.
- Python, NuGet, Gradle, Android, and renderer tool versions are pinned or locked.

## Milestone 1 acceptance tracking

Verified software evidence:

- Versioned authenticated signaling contract and negative tests.
- Real aiortc negotiation with generated 1280x720 video, 48 kHz application audio, and reverse
  audio.
- Native Kotlin/libwebrtc client with video, audio, microphone permission/PTT, status, and
  reconnect.
- Android Studio API 34 emulator run through `adb reverse` with VP8 video, audio playout, reverse
  microphone frames, and reconnect. This is development evidence only.
- Renderer-neutral named-memory protocol with torn-write rejection, bounded audio, restart
  handling, silence fallback, and deterministic Python tests.

Godot migration work:

- ADR-0003 selects MIT-licensed Godot 4.7.2 .NET; Unity is no longer part of the repository stack.
- `apps/renderer` contains the active Godot project, animated placeholder, 1280x720 `SubViewport`,
  two-second application-owned tone, and shared-memory video/audio publishers.
- Checksum-pinned bootstrap, headless import, C# build, renderer self-test, and Windows export pass.
- The bounded local runtime probe passes with changing non-black frames and non-silent PCM; the
  supervised audible tone stopped after two seconds.
- Godot-originated non-black 1280x720 video and 48 kHz PCM reached the aiortc peer, Android
  reported a first rendered 1280x720 frame, and emulator microphone frames returned to Windows.
- Disconnect/reconnect passed with a second non-black Godot video publication and a second
  microphone return. Teardown produced no unobserved task exception, and retained tone PCM was not
  replayed to the new peer.
- The ADB screenshot's WebRTC surface is black and is not used as visual scene evidence. The
  transport/runtime logs and local proof image are recorded separately in `STATUS.md`.

Deferred release acceptance (Milestone 9, not a Milestone 1 blocker):

- Physical Android video/audio/microphone and acoustic behavior.
- Local Wi-Fi, hardware decode/encode, physical lifecycle/teardown, unfocused/monitor-off behavior,
  latency/resource/thermal measurements, and 30-minute stability.
- Production pairing/WSS and release network security; the development token and cleartext
  signaling remain development-only.

Milestones 1 and 2 are complete on their verified software/native-emulator criteria. Milestone 3
may begin. The deferred hardware bundle must remain visible and must pass before Milestone 9 can
complete.

## Milestone 9 target-hardware acceptance tracking

Not executed:

- Physical Android phone on the intended local Wi-Fi network.
- Continuous scene video, teacher audio, microphone return, and independence from PC audio
  hardware.
- Physical lifecycle, interruption, Wi-Fi loss/recovery, reconnect, and state integrity.
- Android hardware decode and Windows hardware encode selection/fallback evidence.
- Pairing, WSS, DTLS-SRTP, firewall, and release-security checks on the physical network path.
- Orientation, acoustics, frame cadence, latency, packet loss, CPU/GPU/RAM/VRAM, thermals,
  unfocused/monitor-off behavior, and 30-minute soak.

These are mandatory release criteria. Emulator results never satisfy them.
