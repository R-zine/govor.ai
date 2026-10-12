# Product roadmap

Status legend: `in progress`, `blocked`, `not started`, `complete` (only when every acceptance
criterion has direct evidence).

| Milestone | Status | Depends on | Acceptance summary |
| --- | --- | --- | --- |
| 0. Repository foundation | complete | Master specification | Source-only bootstrap and full suite pass; contracts, pre-commit, CI syntax, mock mode, and pinned/locked dependencies verified |
| 1. Native streaming proof | complete | M0 foundation | Native emulator diagnostic and Godot media, microphone return, reconnect, cleanup, and development architecture decision pass |
| 2. Session orchestration | complete | M1 architecture decision (satisfied) | Complete validated fake turn cycle across host/Android/renderer; cancellation/timeouts/errors; leak-free repeated sessions |
| 3. Local AI/bilingual | complete | M2 contracts/orchestration | Local LLM/STT, English/Bulgarian/mixed intents, valid structured output, human-speech transcription, measured latency/memory |
| 4. Speech/phonemes | complete | M3 providers | Local English/Bulgarian speech, deterministic fallback, actual-or-null timing, IPA, Android highlighting/replay/rates, and human listening confirmation pass |
| 5. Teaching/progress | complete | M3-4 | Four complete guided scenarios, adaptive explainable teaching, questions do not break lessons, SQLite persistence/resume |
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

Milestone 2 is complete. Its fakes remain available for deterministic development but are not local
AI evidence. Emulator execution remains development evidence only and does not satisfy any
Milestone 9 physical target-hardware criterion.

## Milestone 3 acceptance tracking

Verified local software evidence:

- Pinned llama.cpp b11540 Vulkan and whisper.cpp b5454 CPU runtimes, checksum-pinned Qwen3 and
  multilingual Whisper weights, and a loopback-only development launcher.
- Qwen3 4B and 1.7B Q4_K_M compared on seven English/Bulgarian/mixed structured cases. Both passed;
  the 4B default needed one policy correction versus three for 1.7B and fit the development GPU.
- Real human English and Bulgarian recordings transcribed by whisper.cpp. Both language/keyword
  checks passed; the Bulgarian output had recorded word errors and is not a perfect-accuracy claim.
- Provider-neutral interfaces, explicit health capabilities, deterministic language/intent/policy,
  configurable bounded memory, lesson context, one transient-model retry, and safe scripted fallback.
- Closed model-output schema rejects unknown/control fields. Tests cover clarification progress,
  invalid output, timeout, crash, resource exhaustion, silence, ephemeral files, and capture bounds.
- Real local providers completed a Bulgarian turn followed by an English turn through host
  orchestration with zero retained recordings and zero leaked sessions.

Milestone 3 is complete. At its handoff, the text conversation path was local and returned
naturally to English while its 150 ms diagnostic tone was explicitly not speech evidence.
Milestone 4 has now replaced that local-mode marker with real speech; the historical Milestone 3
fixture limits remain documented separately.

## Milestone 4 acceptance tracking

Verified local software/native-emulator evidence:

- Checksum-pinned Kokoro `en-GB`/`en-US`, Piper `bg-BG`, and deterministic eSpeak NG fallback
  generated bounded non-silent PCM16 WAV.
- Both neural providers returned actual model-derived word/phoneme timing for the benchmark
  phrases; the fallback returned explicit null timing and remained playable.
- Accent-specific curated IPA, Bulgarian-language articulation explanations, strict cross-language
  contracts, full-turn replay, 0.75×/1×/1.25× speed, and isolated-word replay are implemented.
- The API 34 native emulator completed Kokoro playback, seven media-time highlights, 0.75× replay,
  word selection, and separate word playback; cleanup stopped the app, servers, reverse mappings,
  and audio.

Generated English GB/US, Bulgarian, and fallback samples were played synchronously once. The user
confirmed on 2026-10-12 that the GB-English and Bulgarian samples sounded good, closing the
subjective intelligibility/acceptable-naturalness criterion. Milestone 4 is complete.

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

Milestones 1–5 are complete on their verified software/native-emulator and stated human-listening
criteria. The deferred hardware bundle must remain visible and must pass before Milestone 9 can
complete.

## Milestone 5 acceptance tracking

Verified software/native-emulator evidence:

- Four committed functional scenarios each contain objectives, target vocabulary, examples, three
  difficulty prompts, expected learner intents, misunderstandings, completion conditions, gentle
  correction, and Bulgarian help.
- The framework-independent engine completed every scenario in parameterized tests. Bulgarian,
  mixed-language help, questions, repetition, no-speech, and model-proposed progress cannot count
  as successful English production.
- Two failed attempts reduce difficulty; two consecutive first-try successes increase it. Closed
  reason values travel to Android and are covered by deterministic tests.
- SQLite persists active exercise, completion counts, vocabulary/comprehension outcomes,
  difficulty history, English accent, and optional spaced-review state. A reopened database resumes
  an interrupted lesson and contains neither audio nor full transcript fields.
- Android selects all four scenarios plus GB/US accent and review preference, and displays progress.
  The final API 34 emulator UI hierarchy showed every control; no media server or audio was started.
- Local CLI view/export/delete and host final-playback completion behavior pass. The final full
  suite passed with 111 Python tests at 85.69% coverage, 18 contract tests, 13 Kotlin tests, 7 C#
  tests, 15 media tests, Godot validation, and the Android APK build.

Milestone 5 is complete. This evidence establishes deterministic guided progression and local
structured persistence, not broad pedagogical effectiveness or live-human recognition quality.
Milestone 6 may begin; all target-hardware acceptance remains Milestone 9.

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
