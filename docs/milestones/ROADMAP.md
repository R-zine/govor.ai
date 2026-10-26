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
| 6. Avatar/scenes | complete | M1 media decision, M4 timing | Avatar and four validated dynamic environments, lip sync/fallback, memory/performance evidence |
| 7. Optional cloud/privacy | complete | Stable provider interfaces | Independent opt-in providers, offline default, OS secret storage, no unintended cloud/secret logging |
| 8. Packaging/distribution | complete | M1-7 | Portable launcher, signed stable APK/update, integrity-checked models, secure pairing, release lesson, clean shutdown, and clean-Windows VM/host-emulator acceptance passed |
| 9. Release acceptance and target hardware | complete | M8 | Physical Wi-Fi/media/lifecycle/performance, exact post-audit package, explicit Bulgarian-help/English-return flow, café completion/restart, bounded stability, human phone AV confirmation, and final quality gates pass |

## Critical path

M0 reproducibility -> M1 Godot-to-native-emulator media proof and development architecture
decision -> M2 control skeleton -> M3 real local AI -> speech -> teaching/scenes ->
privacy/provider options -> packaging -> M9 physical target-hardware and release acceptance.

Milestone 1 is complete. Its emulator evidence does not satisfy or reduce the mandatory Milestone 9
physical target-hardware bundle.

## Post-milestone maintenance

On 2026-10-22 guided lesson definitions moved from Python/Android constants to strict versioned
JSON in `assets/lesson-content`. The host loads immutable catalog snapshots, Android discovers the
ordered list over the authenticated control contract, and lessons choose a validated reusable
scene template (initially four built-ins). A later maintenance amendment adds a packaged Windows JSON/ZIP picker,
bounded additive import, live whole-catalog replacement, and same-connection Android catalog
updates while preserving active-session snapshots. This work is not a new milestone and does not
revise earlier physical acceptance evidence. See ADR-0013 and the current status handoff.
The 2026-10-23 environment amendment adds bounded data-only procedural ZIPs, live planner swaps,
and dynamic creator choices under ADR-0015; it does not allow application/Godot code patches.
The Android audio-routing maintenance amendment defaults active lessons to the built-in
loudspeaker and restores the prior phone route at teardown; it does not reopen completed physical
acceptance, which predates this application change.
The 2026-10-24 Android presentation amendment replaces the persistent control overlay with three
contextual Material 3 screens. Connection, selection, and active-lesson actions are isolated;
secondary actions use accessible icon menus/sheets, and all prior functionality remains available.
ADR-0017 defines the boundary. Native-emulator verification is new software evidence only and does
not revise the completed physical acceptance record.

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
- `apps/renderer` contains the active Godot project, three selectable CC0 facial teachers, four
  local CC0 photographic backdrops, a 1280x720 `SubViewport`, two-second application-owned tone,
  and shared-memory video/audio publishers.
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

Deferred release acceptance (resolved in Milestone 9, not a Milestone 1 blocker):

- Physical Android video/audio/microphone and acoustic behavior.
- Local Wi-Fi, hardware decode/encode, physical lifecycle/teardown, unfocused/monitor-off behavior,
  latency/resource/thermal measurements, and bounded stability.
- Production pairing/WSS and release network security; the development token and cleartext
  signaling remain development-only.

Milestones 1–7 are complete on their verified software/native-emulator and stated human-listening
criteria. The deferred hardware bundle remained separately visible and later passed in
Milestone 9.

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
Milestone 6 is complete; target-hardware acceptance was deferred to and later passed in
Milestone 9.

## Milestone 6 acceptance tracking

Verified software/native-emulator evidence:

- Three closed CC0 teacher profiles (Elena, Amira, and Daniel) expose 34 facial blend shapes,
  including 14 speech visemes. The pre-connect host menu persists the choice; actual PCM energy
  and provider timing animate its mouth, and speech uses a matching female/male voice.
- A framework-independent planner produces deterministic validated café, supermarket, airport,
  and home specifications from lesson context. Built-ins resolve to four packaged CC0 photographic
  backdrops; installed recipes remain bounded data-only primitives assembled in memory.
- The exported Godot runtime captured four distinct environment frames, transitioned among them,
  cycled all three teacher profiles, and showed zero cache growth plus a 124-byte reported
  video-memory delta on a café revisit. Unknown wire paths are rejected; the internal primitive
  fallback remains deterministic.
- Real Kokoro playback delivered 51 PCM energy samples and 23 provider-timed viseme cues to Godot.
  The no-alignment test path delivered an empty viseme sequence and remained audio-driven.
- The renderer scene tour overlapped two real Qwen3 4B requests. Scene build/transition/frame,
  renderer memory, avatar overhead, and software VP8 encoding were measured and recorded in the
  dated benchmark.
- Godot-originated video still reached native Android while microphone frames returned to Windows;
  this remains API 34 emulator evidence, not physical-hardware acceptance.

Milestone 6 is complete. Physical phone/Wi-Fi/audio, target-machine resource behavior,
monitor-off, thermals, and bounded stability were deferred to and later passed in Milestone 9;
Windows used the accepted software-encoding fallback.

## Milestone 7 acceptance tracking

Verified software and current-user Windows evidence:

- Recognition, dialogue, and speech each select local or OpenAI-compatible cloud adapters without
  coupling the other selections. Fully local remains the default.
- Cloud configuration is rejected while `offline_only` is true. Each cloud adapter checks the
  policy again before credential access and HTTP; a mock transport proves zero network calls.
- Cloud recognition requires a second explicit microphone-upload consent. Privacy documentation
  states exactly which bounded text/audio leaves the PC and that provider retention is external.
- Provider keys use the current user's Windows Credential Manager. A generated throwaway key
  completed real set/status/delete without display, command argument, environment variable, log,
  or retained credential.
- Typed authentication, rate-limit, timeout, transport, and malformed-output failures follow the
  existing recoverable host path. Sentinels for credentials, transcripts, and untrusted response
  bodies are absent from captured logs.
- Complete local deletion securely removes structured history, restores default settings, and
  compacts the database. Existing history-only deletion continues to preserve explicit settings.
- The final full repository suite, dependency audit, and pre-commit hooks pass. No real cloud
  provider, paid account, or learner data was used for acceptance.

Milestone 7 is complete. Provider-specific compatibility, quality, latency, pricing, and external
retention were not tested and are never inferred from mock transports. Milestone 8 may begin.

## Milestone 8 acceptance tracking

Verified software, development-Windows, and native-emulator evidence:

- The repeatable package exports Godot, builds/verifies the signed APK, embeds CPython plus
  hash-locked dependencies, stages llama.cpp/whisper.cpp/application assets, checks package imports,
  and produces an enumerated Windows ZIP plus an artifact digest manifest.
- Guided setup installs six exact model/voice artifacts using pinned revisions, byte sizes, and
  SHA-256 digests with atomic promotion. Normal release startup forces local-only providers.
- The launcher creates a stable TLS identity, short-lived one-time pairing code, authenticated
  HTTPS/WSS gateway, protected per-user state, status output, and clean Windows Job Object teardown.
- The Android release pins the displayed certificate, encrypts its random device credential with
  Android Keystore, and reuses that credential without another pairing code.
- The stable signing identity updated the emulator from signed 0.1.0/code 1 to 0.1.1/code 2 without
  uninstalling. The progress database was byte-identical across the update.
- Signed 0.1.1 connected over its normal emulator router without `adb reverse`, received non-black
  Godot media, returned microphone frames, and completed all three café exercises against the
  packaged local stack. The deterministic final input used the emulator's documented loopback
  microphone injection and is not physical acoustic evidence.
- Normal launcher exit left zero package-owned processes and zero listeners on ports 8765–8768.
- Runtime notices, Python package licenses, shipped govor.ai source, and pinned upstream GPL source
  archives are included and integrity-checked.
- A QEMU 11.0.50/WHPX fixture provisioned the exact digest-recorded user-supplied Windows image,
  froze a clean base, created a disposable qcow2 run overlay, and exposed guest control/media to
  the host Android emulator through loopback-only TCP plus one explicit UDP ICE forward. ADR-0012
  defines the boundary and exact-image limitation.
- The signed 0.1.4/code-5 candidate includes corrected learner wrappers, conditional verified VC++
  prerequisite setup, a 180-second model health window, stdin-based SSH harness execution, and a
  VM-only ICE/tone fixture. Package export/signature/import/doctor and both wrappers passed.
- In Windows 10.0.22000.0 AMD64, `Setup-Govor.cmd` reported the VC++ runtime and all six models
  ready. The signed host emulator connected without `adb reverse`; the guest logged non-black
  1280x720 Godot video, nonzero 48 kHz Godot PCM, and 48 kHz microphone frames. `WaitRelease`
  reported zero listeners/processes and clean shutdown.
- The final full suite, 26-test contract scope, locked dependency audit, and all-files pre-commit
  gate pass. A stale media mypy source-root list found on the first full run was fixed and both the
  focused media scope and complete suite passed afterward.

Historical failure and remaining boundary:

- The first clean-system double-click of the 0.1.1 `Setup-Govor.cmd` failed before model
  installation because its quoted trailing-backslash path consumed the launcher subcommand. The
  0.1.4 clean-guest run directly verifies the corrected wrapper; the historical failure is not
  erased.
- The user-supplied ISO's SHA-256 was verified, but provenance, activation, and licensing were not
  independently verified. It is test input only and is not distributed with govor.ai.
- Physical Android installation, intended Wi-Fi/firewall path, audio hardware, codecs, lifecycle,
  performance, monitor-off behavior, and bounded stability remained the distinct Milestone 9
  bundle and later passed there.

Milestone 8 is complete. Exact evidence and transient failures are in
`docs/benchmarks/2026-10-15-release-packaging-and-distribution.md`,
`docs/benchmarks/2026-10-17-m8-local-vm-fixture.md`,
`docs/benchmarks/2026-10-19-m8-clean-vm-acceptance.md`, ADR-0011, and ADR-0012.

## Milestone 9 target-hardware acceptance tracking

Verified on the documented target path on 2026-10-21:

- A physical realme RMX3939 (Android 16/API 36) connected to the target Windows/RTX 3060 machine
  through the intended WPA2-Personal Wi-Fi with no `adb reverse` mapping.
- First pairing, certificate-pinned HTTPS, stored-credential reuse, authenticated WSS, DTLS-SRTP,
  physical microphone return, explicit disconnect/reconnect, background/foreground, Wi-Fi
  loss/recovery, and clean teardown passed while preserving café lesson state.
- Android used the hardware `c2.unisoc.vp8.decoder`. Windows used measured VP8 software encoding;
  that fallback is explicit and met the cadence target.
- A historical 1,800.065-second transport/media run produced 30.018 emitted fps and 29.726 unique Godot fps,
  zero reported video/audio packet loss, continuous microphone frames, bounded RAM/PSS/VRAM, and
  recorded latency, CPU/GPU, thermals, Wi-Fi ping, unfocused, and monitor-off evidence.
- Muting the Windows playback endpoint did not stop the phone lesson state from advancing to
  learner input. Only phone microphone frames enter the capture path; the application does not
  open a PC microphone.
- On 2026-10-22 the exact signed post-audit `0.1.11`/code 12 candidate passed a fresh 30-second
  physical Wi-Fi benchmark: 30.482 emitted fps, 29.959 unique Godot fps, +1,532 microphone frames,
  zero reported RTP loss, connected DTLS, and hardware Android VP8 decode.
- The same exact candidate completed the café lesson through physical phone microphone input,
  entered Bulgarian clarification/help after recognition ambiguity and returned to English, saved
  completion, reconnected after a clean package restart, retained progress, displayed
  IPA/pronunciation help, and played bounded isolated-word audio.
- On 2026-10-22 a bounded local Piper utterance saying `Какво означава order?` traversed the
  physical phone microphone. Whisper rendered the final transcript as `(speaking in foreign
  language)` rather than preserving the words, but the teacher supplied Bulgarian guidance and
  returned to an English prompt. Bounded Kokoro answers were then recognized, advanced the same
  attempt to 3/3, and the learner opened `Would /wˈʊd/` with Bulgarian pronunciation help. This
  closes the explicit Bulgarian-flow step with the recognition limitation recorded; it is not a
  human-speech accuracy claim.
- The 2026-10-22 product decision removed any fixed-duration continuous lesson or soak as a
  release gate. Bounded interactive, stability, lifecycle, and teardown checks remain required;
  the historical 1,800-second run is retained only as additional evidence.

Final manual evidence:

- On 2026-10-22 the learner confirmed that the final physical phone showed the moving
  teacher/environment and that teacher speech was audible and intelligible.

Milestone 9 is complete. Its physical rows come from the documented target PC, physical phone, and
intended Wi-Fi execution; emulator results do not satisfy or replace them.

## Post-milestone local lesson creator

The next maintenance feature adds a packaged host-side lesson creator without reopening any
completed milestone. `Create-Lesson.cmd` accepts a required topic plus optional content difficulty,
validated installed environment, and one-to-eight exercise length. Omitted values are resolved
deterministically. The existing loopback Qwen/llama.cpp backend generates only the bounded lesson
content; application code owns IDs, ordering, scene selection, final lesson validation, and locked
additive publication. The existing catalog watcher makes the new lesson available to connected
Android clients without a restart. ADR-0014 defines this boundary.

Acceptance for this maintenance item requires structured-output/provider tests, deterministic
default tests, real importer publication, contract fixtures, launcher/distribution checks,
PowerShell parsing, one bounded real local-model smoke when the installed model is available, and
the normal software/pre-commit gates. It does not require rerunning completed physical-device or
clean-VM acceptance unless those paths change.

## Post-milestone patchable environments

The 2026-10-23 maintenance feature makes 3D environments local data patches without reopening completed
milestones. A packaged `Manage-Environments.cmd` ZIP picker installs one or more strict version 1
JSON recipes into `content/environments`. Recipes are deliberately limited to validated colored
box/cylinder/sphere primitives plus closed camera, lighting, and transition presets; they cannot
patch Godot/application code or name models, textures, paths, URLs, scripts, or assemblies. The
host swaps immutable planner snapshots, the lesson importer/creator discovers installed IDs, and
the next lesson sends the primitive recipe to the running Godot renderer. ADR-0015 defines this
boundary.

Acceptance passed through atomic/bounded ZIP security tests, schema and cross-language renderer-contract
tests, live host-registry tests, dynamic lesson-creator choices, package/UI checks, Godot
import/build/self-test, PowerShell parsing, and the normal software/pre-commit gates. This local
content feature does not change or require repetition of completed clean-VM or physical-device
acceptance.

## Post-milestone signed application patches

The 2026-10-23 maintenance feature adds offline updates for host/application changes without
weakening the data-only lesson/environment boundaries. Updater-capable full releases pin a
dedicated RSA-3072 public key and carry a stable `Apply-Govor-Patch.cmd` bootstrap. A signed
`.govorpatch` binds one exact base/target pair, old/new size and SHA-256 values for closed
add/replace/delete operations, and an optional signed-release APK. The installed verifier rejects
tampering, unsafe/extra/colliding paths, wrong bases, local conflicts, active services, and changes
to its own bootstrap/trust key; it stages before mutation, commits the release marker last, rolls
back partial failure, and preserves unlisted imported content plus per-user state. ADR-0016 defines
the boundary.

Android payload handling stops at a verified APK saved on Windows. The learner must transfer/open
it and approve Android's normal update prompt; this feature does not add ADB, silent installation,
unknown-source bypass, or a LAN update endpoint. The historical 0.1.11 acceptance package predates
the trust root and needs one complete updater-capable release replacement. Focused tests and a real
0.1.12 package build verify the new Windows transaction and packaging path; no physical-phone
update was executed, so prior Milestone 9 evidence is neither replaced nor extended.

## Post-milestone QR-first release pairing

The 2026-10-25 maintenance feature replaces error-prone manual first pairing with one locally
displayed and locally scanned QR. The launcher creates a strict `pairing.bootstrap` envelope and
temporary PNG; Godot displays it outside the captured video surface; Android validates it and
enters the existing certificate-pinned HTTPS/WSS credential lifecycle. Stored-host reconnect is a
primary action, while all manual fields remain available behind a collapsed diagnostic section.
ADR-0018 defines the security and UI boundary.

Acceptance requires JSON Schema/launcher/parser tests, a Segno-to-ZXing compatibility fixture,
Godot build and bounded player smoke, signed-release assembly, release UI/scanner verification,
dependency audit, full suite, and pre-commit gate. A physical camera scan is valuable regression
evidence but does not reopen or replace the completed Milestone 9 candidate. The separate mixed
Ethernet/Wi-Fi assessment was recorded in deployment architecture and is implemented by the
subsequent LAN-topology maintenance feature.

The host-side follow-up replaces the QR-over-3D presentation with a dedicated opaque 2D
pre-connect state. It contains network guidance, QR expiry/status, a collapsed manual fallback,
and transitions to the 3D scene only at `session_started`. The release launcher supplies the
fallback through a second protected temporary bootstrap artifact and removes both artifacts at
shutdown; secret values remain absent from process arguments and WebRTC video. The Godot project
and exported Windows executable also use the project-owned govor.ai icon.

## Post-milestone mixed Ethernet/Wi-Fi LAN support

The 2026-10-25 maintenance feature replaces sorted hostname lookup with deterministic Windows
adapter selection. Only active physical RFC1918 adapters with a recognized Windows profile are
eligible; unidentified, virtual/VPN, disconnected, loopback, link-local, and non-RFC1918
candidates fail closed. Private profiles are preferred. The 2026-10-26 correction permits a
Public-category RFC1918 link with a prominent trusted-router/firewall warning because Windows'
category does not determine address scope. The default follows route metrics within the preferred
category. A bounded `--lan-address` override can select another eligible address on a multi-homed
PC but cannot weaken those controls. The existing gateway binds and WebRTC candidate gathering
remain unchanged because they already support a wired host and Wi-Fi phone on one routable trusted
LAN. ADR-0019 records the amended decision.

Unit and launcher gates cover inventory parsing, filtering, route preference, explicit selection,
and failures. Physical acceptance requires the intended Ethernet-to-access-point topology, a
firewall allowance for the selected Windows profile/local network, TCP 8765/8766, authenticated
WSS, ICE/media, and microphone return. Router guest isolation or unrouted VLANs remain documented
deployment failures, not conditions the application bypasses.

## Post-milestone photographic scenes and selectable teachers

The 2026-10-26 presentation feature replaces the blocky procedural teacher with three selectable
CC0 skinned models and replaces the four built-in procedural rooms with reviewed CC0 photographic
2D backdrops. The pre-connect host menu persists Elena, Amira, or Daniel and sends the closed ID to
the host over the existing loopback renderer-control connection. Local and optional cloud speech
resolve the active profile at synthesis time; female profiles use female voice presentations and
Daniel uses male presentations. Accent selection remains independent.

The model, backdrop, and voice mappings are application-owned. Lesson/model output cannot choose a
resource path or voice name, and environment ZIPs remain data-only primitive recipes. Acceptance
requires provenance/hashes, schema and language-binding tests, voice-routing tests, Godot
import/self-test/export, a visual UI proof, the four-scene/profile tour, the full software suite,
dependency audit, and all-files pre-commit. This maintenance feature does not rewrite the completed
Milestone 9 physical evidence; ADR-0020 defines the current visual/voice architecture and limits.
