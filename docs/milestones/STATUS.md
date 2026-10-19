# Current verified status

Last updated: 2026-10-19

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
logging, and bounded cleanup.

Milestone 3 is complete. The local path now uses real pinned llama.cpp/Qwen3 dialogue and
whisper.cpp multilingual recognition, provider-neutral interfaces, conservative language/intent
detection, deterministic bilingual policy, lesson context, configurable bounded memory, explicit
capabilities, bounded retry/fallback, and ephemeral WebRTC microphone capture. Real English and
Bulgarian human recordings and a two-turn host integration passed. At the Milestone 3 handoff, its
response sound was an explicitly labeled 150 ms diagnostic tone; Milestone 4 replaced that marker.

Milestone 4 is complete. Local mode now uses
Kokoro for explicit British/American English, Piper for Bulgarian, and process-isolated eSpeak NG
fallback, with accent-aware IPA, actual-or-null timing, synchronized Android highlighting,
0.75×/1×/1.25× speed, full replay, pronunciation inspection, and isolated-word replay. Automated,
native-emulator, and local-provider evidence passed, and the user confirmed on 2026-10-12 that the
generated GB-English and Bulgarian samples were intelligible and acceptably natural.

Milestone 5 is complete. The host now owns four deterministic guided scenarios, gentle correction,
question/help invariants, explainable bounded difficulty adaptation, scenario selection, and
completion after final teacher playback. Structured settings, exercise/comprehension outcomes,
vocabulary review state, difficulty reasons, completion, and interrupted-session resume persist in
local SQLite without raw audio or full transcript storage. Android exposes all four scenarios,
GB/US accent, optional spaced review, and progress. Local view/export/delete tooling is available.

Milestone 6 is complete. Godot now renders a repository-owned CC0 stylized teacher in validated
procedural café, supermarket, airport, and home environments. The host maps lesson context to a
closed scene specification and maps actual speech PCM plus real-or-unavailable provider timing to
bounded avatar animation. Four-scene runtime, cache/video-memory revisit, software-encoding,
concurrent Qwen3 4B, real Kokoro lip-sync, and native-emulator media paths passed. This is
development evidence; all target-hardware acceptance remains Milestone 9.

Milestone 7 is complete. Independent OpenAI-compatible dialogue, recognition, and speech
adapters, a double-enforced offline-only gate, separate microphone-upload consent, Windows
Credential Manager storage, privacy disclosure, and complete local learner-data deletion are
implemented and verified. Focused tests, the full cross-language suite, the real credential-store
smoke, the deletion CLI smoke, dependency audit, and pre-commit hooks pass. No real cloud service,
paid account, learner recording, or learner transcript was used.

Milestone 8 is complete. The final `0.1.4`/code-5 portable Windows package and signed Android APK
passed packaging, clean-Windows setup/start, authenticated host-emulator control/media, bounded
shutdown, dependency audit, and repository quality gates. The clean guest was Windows
10.0.22000.0 AMD64 under QEMU 11.0.50/WHPX. Its exact user-supplied test ISO was recorded and
SHA-256 verified; provenance, activation, and licensing were not independently verified, and the
ISO is not distributed with govor.ai. Setup installed the pinned Microsoft VC++ prerequisite and
verified all six model artifacts. The host API 34 emulator connected without `adb reverse` over
the fixture's loopback-only forwards; the guest received non-black 1280x720 Godot video, nonzero
48 kHz Godot PCM, and 48 kHz emulator microphone frames. A transient lesson-provider error
recovered through **Retry lesson**, and every bounded launcher run ended with zero release
listeners and zero owned processes.

This VM/emulator result satisfies only the Milestone 8 clean-Windows software row. It does not
satisfy any Milestone 9 physical phone, intended Wi-Fi, acoustic, hardware-codec, lifecycle,
target-performance, monitor-off, thermal, or soak criterion.

ADR-0003 now selects Godot 4.7.2 .NET as the only renderer. The earlier proof from the proprietary
engine was removed completely, including source, project metadata, build scripts, and dependencies.
Godot import, C# compilation, self-test, Windows export, local runtime, non-black shared-memory
video, non-silent application PCM, and emulator delivery have all executed successfully. The
current synchronous `SubViewport.GetTexture().GetImage()` readback is accepted for continued
development. It may still require revision if the mandatory Milestone 9 target-hardware
measurements fail.

## Current implementation

- `apps/renderer` is a Godot 4.7.2 .NET project with a stylized adult teacher, four dynamic
  procedural environments, a dedicated 1280x720 `SubViewport`, and the bounded media-test tone.
- `packages/scene_planner` owns deterministic scene recipes and actual-PCM/provider-timing avatar
  plans without depending on Godot, FastAPI, Android, or provider implementations.
- The version 1 renderer contract accepts only closed asset/environment/camera/lighting/transition
  IDs and bounded transforms. It rejects arbitrary paths, URLs, scripts, and unknown fields.
- Godot caches 68 mesh/material resources, queues replaced scene trees for cleanup, supplies a
  predictable internal missing-asset fallback, and writes no generated 3D files at runtime.
- The teacher blinks/breathes when idle, gestures while speaking, listens/records, thinks during
  processing, and applies encouraging brows/expressions. PCM energy drives mouth opening; six
  viseme shapes are used only when real provider phoneme timing exists.
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
- `packages/provider_interfaces` defines stable recognition/dialogue/speech/lesson types without
  FastAPI, Godot, Android, or runtime dependencies. Host health reports the active provider IDs,
  kinds, locality, and sorted features.
- `services/local_ai` runs Qwen3 4B Q4_K_M through a loopback llama.cpp b11540 Vulkan server and
  multilingual Whisper small through whisper.cpp b5454 CPU. Qwen3 1.7B Q4_K_M is retained as a
  checksum-pinned benchmark comparison, not the selected default.
- Closed structured generation and independent parsing reject extra/control fields. The domain
  policy owns locale and progress, so clarification, reformulation, vocabulary help, repeat,
  slower speech, ambiguity, and recognition errors cannot advance an exercise.
- Conversation memory is scoped to one control connection and compressed to a configurable recent
  window (eight turns by default). Model unavailability/timeout receives one bounded retry and then
  a deterministic response; resource exhaustion/malformed output falls back immediately.
- The media peer resamples microphone frames into one bounded 16 kHz mono capture. Only loopback
  start/finish/cancel endpoints expose the in-memory WAV to the host. whisper.cpp temporary WAV and
  JSON files are removed after every result, including failures.
- Empty valid recognition is treated as no speech, not malformed provider output: no transcript is
  invented, no memory entry is stored, and the learner receives a Bulgarian request to repeat.
- `services/speech` routes `en-GB` and `en-US` to distinct Kokoro v1.0 voices, `bg-BG` to the
  Bulgarian Piper voice, and bounded provider failures to an eSpeak NG subprocess. Text crosses the
  fallback boundary over stdin and is neither a command-line argument nor a log field.
- Pronunciation metadata has exact character ranges, explicit locale, IPA, and optional Bulgarian
  articulation notes. Kokoro duration output and Piper model sample counts become integer
  microseconds only when provider word groups exactly match independent tokenization; otherwise
  alignment is null.
- Android decodes 16/22.05/24/48 kHz mono PCM16 WAV, uses `AudioTrack` media frames for highlight
  time, and exposes replay, three rates, word buttons, IPA/explanation, and isolated-word audio.
  Full replay cannot send a second lesson-completion event; word replay preserves
  `awaiting_learner` and refreshes its deadline.
- Android owns bounded WAV playback and the real WebRTC push-to-talk microphone lifecycle. Godot
  connects outbound to a loopback-only control endpoint and accepts only six visual actions.
- The emulator smoke deliberately exercises renderer-unavailable recovery before completing a
  teacher/learner/teacher turn, media reconnect, renderer reset, and process/network cleanup.
- `packages/domain` defines café, supermarket, airport, and home lessons with three exercise types
  each, committed vocabulary/examples/misunderstandings/Bulgarian explanations, and a pure
  `TeachingEngine`. The LLM may classify intent but cannot award success or choose progression.
- Two unsuccessful English attempts lower difficulty one level; two consecutive first-attempt
  successes raise it. `repeated_difficulty` and `consistent_first_try_success` are validated and
  visible to Android. Bulgarian/mixed assistance, questions, repetition, and no-speech do not count
  as English production or advance an exercise.
- `packages/progress` owns schema-versioned SQLite persistence at the configurable development path
  `data/progress.sqlite3`. It stores structured settings/counters/vocabulary review/difficulty
  history only. An active lesson resumes after process restart; a completed scenario begins a new
  attempt while retaining history.
- `scripts/progress.ps1` views and exports the structured JSON history and requires
  `-ConfirmDelete` before deleting history. Deletion preserves explicit learner settings;
  `DeleteAll` also restores those settings to defaults.
- `services/provider_router` independently composes local/cloud recognition, dialogue, and speech.
  Cloud requests require `offline_only=false`; microphone upload requires separate consent.
- OpenAI-compatible adapters accept only credential-free HTTPS base URLs, expose privacy-relevant
  capabilities, categorize provider failures, and retain actual-or-null timing semantics.
- Provider keys are retrieved on demand from the current user's Windows Credential Manager.
  Interactive tooling sends a new key over standard input and never displays it.
- `session.start` accepts a scenario, English accent, and review preference. Each host-generated
  `teacher.turn` includes an additive progress snapshot. The host sends completed session teardown
  only after the final audio playback acknowledgement.
- Android exposes two visible rows for all four scenarios, GB/US selection, a spaced-review toggle,
  progress/difficulty display, and an explanation when difficulty changes.
- `apps/launcher` supplies `doctor`, model status/install, and release start commands. It uses an
  embedded Python runtime, persistent `%LOCALAPPDATA%\govor.ai` data, stable TLS identity,
  local-only providers, service health checks, and a kill-on-close Windows Job Object.
- `packages/gateway_security` implements expiring one-time pairing, salted PBKDF2-SHA256 code and
  device-credential storage, constant-time checks, bounded failures, and an eight-device limit.
- Release Android verifies the displayed certificate SHA-256 fingerprint, pairs over HTTPS, stores
  the device credential under an Android Keystore AES-GCM key, and authenticates both control and
  media WSS. Debug cleartext/token behavior remains build-separated.
- `scripts/initialize-release-signing.ps1` creates or retains one ignored ACL-restricted RSA-3072
  signing identity. `scripts/package.ps1` exports Godot, builds and verifies the versioned release
  APK, embeds runtimes/dependencies, stages notices/source, smokes the package, and emits hashes.
- `config/release-models.json`, `release-notices.json`, and `release-sources.json` pin every external
  release download by URI, revision where applicable, byte length, and SHA-256.
- The release package contains learner setup/start commands, Windows/Android guides, exact runtime
  notices, installed Python package licenses, the shipped govor.ai source, and the pinned Piper,
  Phonemizer, eSpeak NG, and espeakng-loader source archives.
- `Install-Prerequisites.ps1` probes the packaged llama runtime and, only when necessary, downloads
  the pinned Microsoft-signed VC++ x64 redistributable, verifies byte length/SHA-256/Authenticode,
  and installs it before model setup. The missing-runtime branch passed in the clean guest.
- The QEMU/WHPX fixture forwards authenticated control/media TCP and one explicit M8-only ICE UDP
  port on host loopback. The ICE bridge advertises only the private emulator host alias and is
  enabled solely by fixture environment variables; ordinary LAN/release behavior is unchanged.
- Normal release rendering starts silently. The VM fixture alone requests one locally muted,
  90-second-delayed application tone; Godot still publishes exactly two seconds of PCM and stops.

## Verification ledger

| Command or check | Result | Evidence and limits |
| --- | --- | --- |
| `./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -NoDownload` | verified passing | Pinned local Python/.NET/Godot assets and locked dependencies restored without a download |
| `./scripts/test.ps1 -Scope all` | verified passing | 2026-10-19 final M8 run; Python, contracts, Kotlin, C#, media, Godot, and Android debug APK build all passed from the beginning after the two recorded formatting-only attempts |
| Python gate | verified passing | Ruff check/format, strict mypy, 169 tests, 85.51% branch coverage |
| Contract schema gate | verified passing | 26 schema/model/fixture tests include closed scene/avatar payloads, gateway authentication, and arbitrary-asset rejection |
| Kotlin gate | verified passing | 13 JVM contract/state-machine/timeline tests, including lesson-progress invariants and shared fixtures |
| Pure C# gate | verified passing | 8 .NET contract/allow-list tests, including scene/avatar validation and arbitrary-asset rejection |
| Media gate | verified passing | Strict mypy across media/contracts/gateway-security and 18 tests, including real aiortc loopback, authenticated signaling, VM ICE connection, flushed 48-to-16 kHz microphone resampling, renderer-buffer validation, and clean remote-track teardown |
| Godot gate | verified passing | Headless import, successful C# build, and self-test marker; offline NuGet vulnerability lookup and Windows certificate-store warnings are recorded below |
| `./scripts/build.ps1 -Target renderer` | verified passing | 109,372,928-byte executable SHA-256 `65d86d986f0f5508a2dede1bce653bfb21fc6fd8cf06aed43872c0806e679175`; 91,648-byte renderer DLL SHA-256 `31dd5c9355cc81d4df51c0168dc7e0f3c60dc8d5016560537c13244210884c39` |
| `./scripts/renderer-scene-smoke.ps1` | verified passing | Four distinct 1280x720 café/supermarket/airport/home captures; zero fallbacks, cache growth, or video-memory growth on revisit; software VP8 measured |
| `./scripts/benchmark.ps1 -Profile renderer` | verified passing with limits | Scene tour overlapped two real Qwen3 4B requests; frame p95 33.459 ms, scene build max 1.210 ms, transition max 376.994 ms, avatar 27.826 µs/frame, software VP8 p95 6.640 ms |
| `./scripts/renderer-smoke.ps1` | verified passing | Final run: 5 complete/changing frames, RGB maximum 255, 7 PCM blocks, peak 2621; proof PNG and clean bounded exit |
| Supervised audible renderer smoke | verified passing | Brief PC check only; tone completion marker at two seconds and process stopped |
| `./scripts/emulator-renderer-smoke.ps1` | verified passing with limits | Complete fake turn, café scene, PCM-energy/no-viseme fallback, and recovery; final Android interval was 120/120 frames, zero drops, 4.001 seconds (30.0 fps); video and microphone return passed after reconnect |
| `./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi` | verified passing | Pinned/checksummed runtimes, two Qwen candidates, Whisper model, and human-speech fixtures available; comparison model downloaded from the pinned official revision |
| `./scripts/benchmark.ps1 -Profile local-ai` | verified passing | 2026-10-12 regression: Qwen3 4B and 1.7B each passed 7/7 bilingual structured cases; two real STT fixtures and two-turn host integration used real Piper/Kokoro audio, retained no recordings, leaked no sessions, and stopped all local servers |
| `./scripts/test.ps1 -Scope speech` | verified passing | Strict speech/provider mypy and 11 tests covering both neural adapter shapes, real eSpeak subprocess output, fallback routing, accent IPA, timing/null fallback, WAV bounds, and factory wiring |
| `./scripts/benchmark.ps1 -Profile speech` | verified passing | Real Kokoro GB/US, Piper Bulgarian, and eSpeak fallback generated non-silent WAV; neural timing present, fallback timing null, speed duration ordered, IPA regression passed |
| Speech benchmark latency | verified with limits | Final 1× examples: Kokoro GB 403.7 ms, Piper BG 784.9 ms, eSpeak fallback 276.5 ms; cold/accent cases recorded separately; development CPU only |
| `./scripts/emulator-speech-smoke.ps1` | verified passing with limits | API 34 emulator completed real Kokoro playout/highlighting/replay/word audio; Godot applied the café scene plus 51 PCM energy samples and 23 provider-aligned visemes; clean shutdown |
| Generated speech listening path | verified passing | GB English, US English, Bulgarian, and fallback WAVs each completed one synchronous PC playback and closed; the user confirmed the GB-English and Bulgarian samples sounded good on 2026-10-12 |
| Four guided scenarios | verified passing | Parameterized pure-domain tests completed café, supermarket, airport, and home; each has three exercises and full committed guidance metadata |
| Adaptation/help policy | verified passing | Repeated difficulty lowers one level, two first-try successes raise one, closed reasons are exposed, and Bulgarian/mixed/help/no-speech turns cannot advance |
| SQLite progress/resume/privacy | verified passing | Closed/reopened database resumed the next exercise; history/settings/vocabulary/review/export/delete passed; a sentinel transcript and audio fields were absent |
| Offline/cloud configuration gate | verified passing | Defaults are fully local with `offline_only=true`; every cloud selector is rejected under that default, and cloud STT requires separate microphone-upload consent |
| Independent provider composition | verified passing | Tests built fully cloud and mixed local/cloud pipelines and observed expected recognition/dialogue/speech locality without an outbound request |
| Cloud adapter contract/error handling | verified passing with mock limit | In-process transports covered strict JSON dialogue, bounded WAV upload, streamed response ceilings, WAV speech/null timing, missing/rejected credentials, typed failures, and privacy-safe logs; no vendor compatibility claim is made |
| Offline runtime network block | verified passing | A constructed cloud adapter under the offline policy accessed neither the credential store nor its mock HTTP handler |
| Windows protected credential storage | verified passing | A generated throwaway value completed actual current-user Credential Manager set/status/delete; it was stdin-only, undisplayed, and deleted in a `finally` path |
| Complete learner-data deletion | verified passing | Unit and CLI smokes removed all structured history, restored defaults, enabled SQLite secure deletion, compacted the database, and retained no deleted scenario identifier bytes |
| Host lesson completion | verified passing | Local-service integration completed café and persisted it; host waited for final playback before `session.ended: completed` |
| Android Milestone 5 UI | verified passing with emulator limit | API 34 final UI hierarchy showed Café, Supermarket, Airport, Home, GB/US, and optional review; app was force-stopped and no media/audio server was started |
| Qwen3 4B dialogue | verified passing with limits | 999.3 ms median, 2,784.6 ms max; 1 policy correction; 2,706,419,712-byte working set and 3,207,090,176-byte peak on this machine |
| Qwen3 1.7B comparison | verified passing with limits | 630.4 ms median, 2,570.1 ms max; 3 policy corrections; 1,309,011,968-byte working set; comparison only |
| whisper.cpp human recordings | verified passing with limits | English and Bulgarian language/required-word checks passed at 5,840.2 ms median; Bulgarian had word errors; no broad accuracy claim |
| Local-provider host turn | verified passing | Bulgarian fixture then English fixture completed one session with Piper then Kokoro audio, returned to English, dispatched expected renderer states, retained zero recordings, and leaked zero sessions. Both free-form replies safely returned null alignment when provider groups did not exactly match tokenization. |
| `./scripts/dev.ps1 -Mode local ...` | verified passing | Host, renderer, media, and llama.cpp health passed on loopback; health exposed the three real/diagnostic capabilities; terminating the foreground host stopped ports 8765–8768, Godot, and llama.cpp |
| Godot emulator screenshot | inconclusive | UI/status captured, but the WebRTC `SurfaceView` area is black in ADB screencaps; transport logs prove non-black input and Android render callbacks, not a screenshot of scene pixels |
| Renderer-source reconnect/teardown | verified passing on emulator | Second peer received non-black Godot video and microphone frames; no unobserved task exception and no retained tone block replay |
| Milestone 1 development architecture gate | complete | ADR-0002/0003 confirmed on native-emulator evidence; ADR-0004 defers all physical target-environment acceptance to Milestone 9 |
| Android APK build | verified passing | 58,726,666 bytes; SHA-256 `ee37f03b47176d30d20d902807d86f43d2bb1c039b2de5e2d1b7b8aa97ada3d8` |
| Release signing initialization/repeat | verified passing on development Windows | RSA-3072 JKS plus properties remained ignored and ACL-restricted; second run retained the same identity; no secret was printed or packaged |
| `./scripts/package.ps1 -Version 0.1.1 -VersionCode 2 -NoArchive -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline` | verified passing | Godot export, signed Android release build/signature, 56 hash-pinned Python distributions, runtimes/source/notices, import smoke, and launcher doctor passed |
| `./scripts/package.ps1 -Version 0.1.1 -VersionCode 2 -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline` | verified passing | Final portable-directory, signed-APK, artifact-manifest, and ZIP production passed; ZIP 310,891,123 bytes, SHA-256 `a801b1b8...a4d`, enumerated successfully, and contains the corrected verification source |
| Clean-system `Setup-Govor.cmd` from 0.1.1 | **verified failing** | Double-click reached argparse without a command because quoted `%~dp0` ended in `\` and consumed the following token; setup reported that no unverified model file was installed |
| `./scripts/package.ps1 -Version 0.1.2 -VersionCode 3 -NoArchive -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline` | verified passing | Corrected candidate normalized the install root and package-time `cmd.exe` smokes exercised both learner-facing wrappers through `doctor`; each printed `Package prerequisites: ready` |
| `./scripts/package.ps1 -Version 0.1.2 -VersionCode 3 -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline` | verified passing | Corrected ZIP 310,894,467 bytes, SHA-256 `816d503a...034f`; archive enumerated, emitted wrappers inspected, and direct/setup/start doctor paths passed |
| Signed 0.1.2 APK | verified packaging only | 55,425,169 bytes; SHA-256 `153101ab250774249fa7048101998d2cda8ed8176a82893e083bc8d49f4fdaa5`; package code 3/name 0.1.2 with the existing RSA-3072 signer; clean-system/client retry not yet executed |
| `./scripts/package.ps1 -Version 0.1.3 -VersionCode 4 -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline` | verified passing | The VM-testable wrapper candidate passed Godot export, signed APK verification, dependency/source staging, import smoke, direct doctor, both command-wrapper doctors, and archive creation |
| 0.1.3 VM-testable artifacts | verified packaging only | ZIP 310,917,484 bytes/SHA-256 `4d30b7ee...86bd`; APK 55,425,169 bytes/SHA-256 `175265c7...8bc0`; existing RSA-3072 signer, version code 4/name 0.1.3 |
| `./scripts/m8-vm.ps1 -Action Prerequisites` (2026-10-17) | historical blocked result | QEMU/qemu-img/EDK2/WHPX/OpenSSH, 31.8 GiB RAM, and 461 GiB free passed; no ISO had yet been supplied. The completed 2026-10-19 run supersedes this pre-execution result |
| Bounded QEMU fixture probe | verified passing with boot-only scope | WHPX/q35/pflash UEFI/quoted paths/IDE qcow2 process remained alive for three seconds and was stopped; Windows/Godot did not boot and are not inferred |
| VM fixture regression tests | verified passing | Focused tests cover wrapper forwarding, fixed TCP/UDP loopback topology, test-only delayed PCM, stdin-based SSH execution, parseable secret-free templates, required actions, pflash, and generated-key SSH setup |
| `./scripts/package.ps1 -Version 0.1.4 -VersionCode 5 -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline` | verified passing | Godot export, signed APK verification, embedded runtime/dependency/source staging, import/doctor/wrapper smokes, VC prerequisite metadata, and final archive creation passed |
| Final 0.1.4 artifacts | verified passing | ZIP 310,942,015 bytes/SHA-256 `74899c85222faf65681e9512eafaee5c2dc05e79daf06d338148255ae801b838`; APK 55,425,169 bytes/SHA-256 `78799b5f943fe0caba08e9cada443ba40e42c8a4e6f1424b7c081129ebd43358`; RSA-3072 signer SHA-256 `b7022cb8bbcc0a4828cf73e5ef958e1b431ccce697020577c4a502a66ec59843` |
| Clean-VM `StageRelease` / `SetupRelease` | verified passing | Guest independently matched both artifact hashes, exact packaged `Setup-Govor.cmd` passed, Microsoft VC++ runtime reported ready, and all six pinned models reported ready |
| Clean-VM `StartRelease` with host signed APK | verified passing with VM/emulator limits | Windows 10.0.22000.0 guest launched the actual Godot/local-AI stack; signed 0.1.4/code-5 emulator app reused its credential with no `adb reverse`; WSS/ICE connected and media logged non-black 1280x720 video, nonzero PCM peak 2621, and 48 kHz/960-sample microphone frames |
| Clean-VM bounded shutdown | verified passing | Final `WaitRelease -SmokeSeconds 300` recorded task `Ready`, zero listeners, zero owned processes, and `clean_shutdown=true`; emulator and VM were then stopped, leaving no tone or server active |
| Signed 0.1.1 APK | verified passing | 55,425,169 bytes; SHA-256 `7e372b5b487d47e85018b55c9aceca03c7ced6c4a7822f764b0471d5270b755a`; package code 2/name 0.1.1, min 26/target 34; RSA-3072 certificate digest recorded in the dated benchmark |
| Signed 0.1.0-to-0.1.1 emulator update | verified passing with emulator limit | `adb install -r` preserved first-install time and existing encrypted device credential; progress DB SHA-256 remained `4add036f...e41` immediately across the update |
| Release pairing/credential reuse | verified passing with emulator limit | First pairing used HTTPS plus a pinned displayed fingerprint; later 0.1.1 connection entered only `10.0.2.2` hosts and reused the Android Keystore credential over WSS without `adb reverse` |
| Complete packaged release lesson | verified passing with emulator limit | Signed APK and packaged local stack completed café 3/3 and displayed `Lesson complete · progress saved`; final deterministic PCM used the emulator's loopback microphone injection, not physical acoustics |
| Release progress after lesson | verified passing | Isolated SQLite view reports café `completed_count=1`, `exercise_index=3`, `successful_exercises=3`; 45,056 bytes, SHA-256 `0b5523f3...df84` |
| Release shutdown | verified passing | Launcher Job Object/stop path closed children; final check found zero package-owned processes and zero listeners on ports 8765–8768; app/emulator stopped and no audio remained |
| Release notices/corresponding source | verified passing | Hash-pinned Godot/llama.cpp/whisper.cpp/WebRTC notices, Python/.NET/LLVM notices, installed package licenses, shipped source, and four exact GPL upstream archives were staged |
| Clean Windows package installation | verified passing with exact-image/VM limit | The historical 0.1.1 wrapper failure remains recorded. The corrected 0.1.4 package completed setup/start/host-emulator media/stop in the provisioned guest; this is clean-software evidence, not target hardware evidence |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-m2-final` | verified passing | Final Milestone 2 audit: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-m3-final` | verified passing | Final Milestone 3 audit: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m4-final` | verified passing | Final Milestone 4 audit, including media and speech extras: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m5-final` | verified passing | Final Milestone 5 audit: no known vulnerabilities found; the sandbox-denied query passed with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m6-final` | verified passing | Final Milestone 6 audit: no known vulnerabilities found; the sandbox-denied query passed with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m7-final` | verified passing | No known vulnerabilities found |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m8-entrypoint-fix` | verified passing | 2026-10-17 corrected-candidate locked dependency graph: no known vulnerabilities found with approved metadata access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m8-vm` | verified passing | 2026-10-17 VM-fixture locked dependency graph: no known vulnerabilities found after the sandbox-denied metadata request was approved |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m8-final` | verified passing | 2026-10-19 final locked dependency graph: no known vulnerabilities found |
| Pre-commit across all tracked/untracked sources | verified passing | 2026-10-19 final `pre-commit-m8-final` run passed JSON/YAML, line endings/whitespace, secret/size checks, Ruff, formatting, and 26 contract tests using command-scoped safe-directory configuration |
| `./scripts/hardware-test.ps1` | Milestone 9 not executed | Ignores the active emulator and exits 2 because no physical phone is connected; this does not reopen Milestone 1 |
| Physical Android/Wi-Fi/media/soak bundle | Milestone 9 not executed | No suitable physical phone; mandatory before release, not a prerequisite for Milestones 2-8 |
| Remote GitHub Actions | not executed | Workflow includes the Godot renderer job, but the current milestone snapshot has not run remotely |

The final `./scripts/test.ps1 -Scope all` run passed on 2026-10-19: 169 Python tests at 85.51%
branch coverage, 26 dedicated contract tests, 13 Kotlin tests, 8 pure C# tests, 18 media tests,
Godot import/build/self-test, and the Android debug APK build. The first final attempt stopped at
one Ruff line-length error in a launcher regression test. After that mechanical wrap, the second
stopped at format-check differences in `fixture_ice.py` and its integration test. The pinned
formatter corrected only those two files, and the complete suite then passed from the beginning.
Earlier M8 runs had also exposed and corrected the gateway-security mypy source root and the
trusted static-XML test formatting; those historical attempts remain recorded in the dated files.
Pytest emitted the existing Starlette `httpx` deprecation warning. Godot could not read the Windows
root-certificate store and NuGet could not refresh online vulnerability metadata inside the
sandbox; these were non-fatal environment warnings and every gate completed successfully.

## Milestone 3 acceptance and handoff

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| Learner can hold a basic English conversation locally | verified passing with limits | Real Qwen3 handled the English fixture and a two-turn local-provider host session; response text traversed the host contract. The audio marker is not TTS. |
| Bulgarian clarification requests work | verified passing | Both model candidates returned the expected Bulgarian clarification intent/locale; policy tests prove the request cannot advance the exercise. |
| Teacher returns naturally to English | verified passing | One host session processed Bulgarian then English human recordings and emitted `bg-BG` then `en-GB` teacher turns with bounded history. |

Implementation and decision details are in ADR-0006 and the dated benchmark. There is no current
Milestone 3 blocker. The first Python gate exposed 83.47% coverage and was fixed with adapter-boundary
tests. The first comparison-model bootstrap and dependency audit were denied by sandbox networking
and passed when repeated with approved network access. The first final pre-commit pass normalized
three generated lock files; the second and post-staging passes were clean. The local launcher health
check required force-stopping only the foreground host because the automation PTY did not deliver
Ctrl+C; its `finally` block then stopped every child/listener as designed.

Not executed for Milestone 3: a live human conversation, Bulgarian-accented English audio, hesitant
or short human audio, and a spoken mixed-language recording. Those are not inferred from text
fixtures. They remain evaluation inputs for future teaching/speech work, while physical-phone,
Wi-Fi, acoustics, codecs, concurrent target load, thermals, and soak remain mandatory Milestone 9
criteria.

## Milestone 4 acceptance and handoff

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| Natural English and Bulgarian speech | verified passing with stated scope | Real Kokoro `en-GB`/`en-US` and Piper `bg-BG` produced non-silent WAVs and traversed native Android playback; the user confirmed GB-English and Bulgarian intelligibility/acceptable naturalness on 2026-10-12. |
| Deterministic offline fallback | verified passing | Two eSpeak NG runs returned byte-identical WAV; provider ID/fallback flag were explicit and timing was null. |
| Word highlighting follows actual speech when available | verified passing with emulator limit | Kokoro/Piper benchmark timing came from model duration/sample output; Android logged all seven Kokoro word indices from playback-head media time. |
| IPA on demand and pronunciation explanation | verified passing with emulator limit | Accent-specific curated IPA regression passed; Android word selection triggered inspection and isolated-word audio. |
| Full/word replay and speech speed | verified passing with emulator limit | 0.75× replay completed without a second host lesson-completion event; provider benchmarks proved ordered 0.75×/1×/1.25× duration; isolated word completed. |
| Missing alignment does not block playback | verified passing | Real deterministic fallback returned null timing; Kotlin timeline returned no highlight and the WAV remained valid/playable. |
| `en-GB` versus `en-US` is consistent | verified passing with bounded scope | Distinct configured voices and locale-specific IPA produced the expected `water`/`schedule` differences. |

Implementation, commands, exact metrics, hashes, transient failures, and limits are recorded in
ADR-0007 and `docs/benchmarks/2026-10-12-local-speech-and-emulator.md`. The GPL speech stack is
acceptable for local development, but Milestone 8 must either meet its distribution obligations or
replace it. The human listening confirmation closes the final Milestone 4 acceptance item; this
handoff is the required focused milestone commit.

## Milestone 5 acceptance and handoff

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| A complete guided lesson can finish | verified passing | Pure-domain tests completed all four scenarios; local-service café integration completed and host teardown waited for final audio acknowledgement. |
| Progress persists after application restart | verified passing | A file-backed SQLite repository was closed/reopened and resumed café at exercise two; a completed lesson retained its completion count and began a fresh attempt. |
| Repeated difficulties adapt the lesson | verified passing | Two unsuccessful English attempts lowered intermediate to beginner and exposed `repeated_difficulty`; tests also cover upward adaptation. |
| Questions do not break the exercise | verified passing | Bulgarian clarification, vocabulary help, repeat, slower speech, no-speech, and mixed-language paths preserve the active exercise and do not increment English success. |
| Bulgarian assistance is not successful English | verified passing | Domain and local-service tests prove Bulgarian production cannot advance even when the model proposes progress. |
| Teacher provides appropriate correction | verified passing with bounded scope | Each committed exercise has a gentle English correction and Bulgarian explanation; tests verify corrective retry text. This is guided-content evidence, not broad pedagogical validation. |
| Difficulty changes are explainable/testable | verified passing | Only the two closed reasons can cross the contract; Python/Kotlin validation and deterministic engine tests pass. |
| Progression and persistence tests | verified passing | The final Python suite contains domain, SQLite, CLI, local-service, and host integration coverage; shared schema/Kotlin/C# fixtures pass. |

Implementation and privacy decisions are recorded in ADR-0008; exact commands, transient failures,
artifacts, and limits are in `docs/benchmarks/2026-10-12-teaching-engine-and-progress.md`. No new
third-party dependency was added. The phrase-pattern evaluator is intentionally scoped to committed
guided tasks and is not a fluency, grammar, or pronunciation score.

The API 34 UI check is emulator development evidence only. No live human lesson or physical phone,
Wi-Fi, codec, acoustic, target-load, thermal, or soak acceptance ran. Those do not block Milestone
5 and remain mandatory Milestone 9 work. This handoff is the required focused Milestone 5 commit.

## Milestone 6 acceptance and handoff

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| Teacher visible in streamed 3D environment | verified passing with emulator limit | Four local 1280x720 captures visibly contain the stylized teacher; renderer-originated non-black video reached native Android at 30 fps with no drops in the final short interval. |
| Speaking animation corresponds to teacher audio | verified passing | The host extracts energy from actual PCM sample positions. Real Kokoro delivered 51 energy samples and 23 provider-timed visemes to Godot for a 2,038,666 µs utterance. |
| At least four environments assemble | verified passing | Exported Godot captured distinct café, supermarket, airport, and home frames with zero fallbacks. |
| Environment responds to lesson context | verified passing | Host integration maps selected scenario to its deterministic scene; the emulator smokes required the café scene marker, and planner tests cover every scenario. |
| Invalid scene specifications rejected | verified passing | Python/JSON Schema/C# validation rejects unknown IDs, bounds, extra fields, and an explicit `../../downloaded-model.glb` fixture. |
| Missing assets have predictable fallbacks | verified passing | Godot self-test invokes an internal unknown catalog item and verifies the named magenta fallback; untrusted unknown wire IDs are rejected earlier. |
| Scene changes do not leak significant GPU memory | verified passing with bounded scope | After all four scenes, a cached café revisit added zero cached resources and zero Godot-reported video-memory bytes. This short run is not a soak claim. |
| Runtime scene data stays in memory | verified passing | Procedural scene nodes/resources are created in memory; the tour writes proof PNGs only in explicit benchmark mode, not generated 3D scene files. |
| Rendering usable beside local inference | verified passing on development PC | Renderer tour/encoding overlapped two Qwen3 4B requests; frame p95 was 33.459 ms at the 30 fps target. |
| Required performance measurements | verified passing with limits | Scene builds 0.243–1.210 ms; transitions 370.550–376.994 ms; cached revisit 0.436 ms; avatar 27.826 µs/frame; software VP8 p95 6.640 ms; memory figures recorded in the dated benchmark. |

Implementation and boundary decisions are recorded in ADR-0009. Exact commands, transient
failures, artifacts, metrics, and limits are in
`docs/benchmarks/2026-10-12-avatar-scenes-and-renderer-performance.md`. No new third-party
dependency or downloaded renderer asset was added.

The real-alignment emulator run proves the control/timing path, not physical display quality or
acoustics. The cache/video-memory revisit is a bounded regression check, not a 30-minute leak test.
Hardware encode/decode, physical phone/Wi-Fi/audio, target-machine resource behavior, lifecycle,
monitor-off, thermals, and soak remain mandatory Milestone 9 work. This handoff is the required
focused Milestone 6 commit.

## Milestone 7 acceptance and handoff

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| Local-only is the default | verified passing | Settings default to three local selectors plus `offline_only=true`; health exposes the offline state |
| Each subsystem can switch independently | verified passing | Composition tests build all-cloud and local-STT/cloud-dialogue/local-TTS pipelines with expected capability order/locality |
| Provider errors are graceful | verified passing | Typed authentication/resource/transport/malformed failures reach existing deterministic dialogue fallback or recoverable host handling |
| Invalid credentials do not crash the app | verified passing | Missing and HTTP 401 credentials raise redacted `ProviderAuthenticationError`; host failure tests retain zero active sessions |
| Cloud cannot occur in offline mode | verified passing | Configuration rejects the combination and the per-request gate prevents credential lookup and mock HTTP after construction |
| Privacy-sensitive data is absent from normal logs | verified passing | Captured logs contain none of the sentinel key, transcript, response body, or audio payload |
| Cloud network calls are disabled by default | verified passing | Default app/settings remain fake/local and offline; the explicit offline adapter test records zero handler calls |
| Credentials use OS-protected storage | verified passing on Windows | Actual current-user Credential Manager set/status/delete succeeded with a throwaway secret removed immediately |
| Stored learner data can be completely removed | verified passing | `DeleteAll` securely deletes history, resets settings, compacts SQLite, and is confirmation-gated |

ADR-0010 records the opt-in, independent-selection, and secret-storage decision. Exact test scope,
limits, and privacy evidence are in `docs/benchmarks/2026-10-14-cloud-privacy-controls.md`; learner-
facing disclosure is in `docs/privacy/cloud-providers.md`. No dependency was added. The first full
Python run passed all 134 then-current tests but failed the coverage gate at 83.22%; isolating the
externally exercised Win32 FFI and adding CLI/store tests produced a passing gate. The final
invalid-credential and streamed-response regressions brought the result to 140 tests at 86.18%
coverage. Provider-specific functionality, quality, retention, and latency remain not executed.

## Milestone 8 acceptance and handoff

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| Clean Windows system installs/launches with the guide | verified passing with exact-image/VM limit | The final 0.1.4 ZIP was independently hashed and extracted in a provisioned Windows 10.0.22000.0 AMD64 QEMU/WHPX guest. Exact packaged setup installed/verified prerequisites and six models; exact packaged start launched the renderer/local stack. The user-supplied ISO's provenance, activation, and licensing were not independently verified |
| Android connects without developer tools | verified passing with emulator limit | Signed 0.1.4/code-5 connected through `10.0.2.2:18765/18766` over certificate-pinned/authenticated WSS and DTLS-SRTP with an empty `adb reverse --list`; ADB installed/automated the emulator, so physical user installation is not inferred |
| Complete lesson works on a release build | verified passing with emulator limit | Packaged local stack plus signed 0.1.1 APK completed café 3/3 and displayed saved completion; final PCM entered through the emulator's documented loopback microphone API |
| Shutdown leaves no orphaned processes | verified passing | Final clean-VM `WaitRelease` reported zero listeners, zero owned processes, and `clean_shutdown=true`; the host emulator and VM then stopped normally |
| Local progress survives updates | verified passing | Signed code-1 to code-2 APK update preserved first-install time, encrypted credential, and byte-identical pre-lesson progress database |
| Signing keys remain private | verified passing on development Windows | Stable ignored RSA-3072 keystore/properties have a restricted ACL and were absent from the package/source bundle/logs; release operator still needs an off-machine private backup |
| Required model downloads have integrity checks | verified passing | Six exact artifacts require byte size and SHA-256 before atomic promotion; clean-guest setup and model status reported every artifact ready. The conditional VC++ download also pins size/hash and verifies Microsoft Authenticode |
| Internet is unnecessary during normal lessons | verified passing with current-machine scope | Complete packaged lesson used the already verified models and forced local/offline providers; guided first-run setup still requires internet |

ADR-0011 records the portable/update/security/distribution decision. Exact package hashes, signing
metadata, commands, transient failures, lesson evidence, source/notice sizes, and limitations are
in `docs/benchmarks/2026-10-15-release-packaging-and-distribution.md` and
`docs/benchmarks/2026-10-19-m8-clean-vm-acceptance.md`. Learner instructions are in the
Windows/Android guides and the packaged troubleshooting document.

ADR-0012 selects the local QEMU/WHPX clean-Windows fixture. Provisioning recorded and verified the
user-supplied ISO at 4,693,557,248 bytes with SHA-256
`15fecff356411d43c77df040e1847427402b0e09da069bf1db0cb754932075b9` before producing a stopped
base and disposable run overlay. The image is not part of the application or its distribution;
this project did not independently verify its provenance, activation, or license. Generated
secrets/disks stayed ignored and ACL-restricted.

The fixture keeps SSH, authenticated WSS, and the single UDP ICE bridge on host loopback. The host
emulator reached the guest through `10.0.2.2`; no nested emulator or `adb reverse` was used. The
M8-only ICE adapter advertised `10.0.2.2:18770` because QEMU user networking otherwise returned an
unreachable guest host candidate. It preserved release WSS plus WebRTC DTLS-SRTP and is enabled
only by fixture environment variables; normal LAN behavior is unchanged.

The first package run inside the managed sandbox could not access the existing external Gradle
cache; the approved run then exposed and fixed an optional notice-manifest property access. The
final no-archive and archive-enabled 0.1.1 packages passed, but their direct-Python doctor smoke did
not exercise the batch entrypoint. The first clean-system double-click exposed the quoted trailing
backslash defect in both Windows wrappers. Version 0.1.2 normalizes `%~dp0` before passing it to
Python, adds a regression test, and runs both packaged wrappers through `cmd.exe` during packaging.
Version 0.1.3/code 4 added bounded launcher-argument forwarding. The final 0.1.4/code-5 package
also fixes clean-guest VC++ prerequisite installation, extends the llama health timeout to 180
seconds, sends SSH harness scripts over stdin rather than command-line encoding, and supplies the
explicit VM ICE forward. Its Windows ZIP is 310,942,015 bytes with SHA-256
`74899c85222faf65681e9512eafaee5c2dc05e79daf06d338148255ae801b838`; its APK is 55,425,169
bytes with SHA-256 `78799b5f943fe0caba08e9cada443ba40e42c8a4e6f1424b7c081129ebd43358`.

The clean guest's exact setup passed after the pinned Microsoft Visual C++ 2015-2022 x64 runtime
was installed. The final setup wrapper reported the runtime and all six models ready. A normal
release starts with no diagnostic tone. For VM acceptance only, the harness requested a locally
muted tone 90 seconds after renderer startup so Android could finish ICE first. The media gateway
then logged a 48 kHz/960-sample renderer block with peak 2621, a non-black 1280x720 frame
(`rgb_min=0`, `rgb_max=255`), and a 48 kHz/960-sample emulator microphone frame. Android logged the
goldfish VP8 decoder at 1280x720, rendered frames, audio playout, and active microphone capture.
Godot's bounded generator publishes exactly two seconds and stops; no local PC sound was enabled.

The lesson control sometimes entered a recoverable provider error during these resource-heavy VM
runs; the exact **Retry lesson** action restored `lesson: ready`. A media disconnect later
coincided with concurrent SSH evidence copying in the counting run, after all required evidence had
been captured. An earlier exact-candidate run retained `media: connected · lesson: ready`. Every attempt
used the same final package and ended cleanly. ADB screenshots intermittently captured the
`SurfaceView` as black even while aiortc and Android renderer logs proved non-black frames; those
screenshots are not used as visible-video evidence.
The initial audio-enabled AVD still
zeroed host input until
the installed emulator's explicit `-allow-host-audio` switch was used. Acoustic playback completed
two turns but was unreliable for the third; the emulator's documented loopback audio injection
then completed the real signed-app PTT path. A tooling delay intentionally exercised the normal
recoverable timeout and **Retry lesson** resumed the persisted third exercise. None of those failed
attempts is reported as a passing physical/acoustic result.

Milestone 8 is complete. A focused milestone commit accompanies this handoff after the final full
suite, locked dependency audit, and all-files pre-commit gate passed. Milestone 9 is next but has
not begun.
The absence of physical phone/Wi-Fi/codec/acoustic/target-performance/monitor-off/thermal/soak
evidence is assigned to Milestone 9 and does not weaken or expand this software-only M8 result.

## Renderer evidence and limitations

The current local proof images visibly contain the stylized teacher in four distinct procedural
environments. The live bridge probe observed multiple changing frames and explicitly rejected an
all-black stream. In the emulator run, the aiortc peer logged non-black input, Android
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

Initial migration evidence is in `docs/benchmarks/2026-10-09-godot-renderer-migration.md`; current
avatar/scene evidence is in
`docs/benchmarks/2026-10-12-avatar-scenes-and-renderer-performance.md`.

## Environment and artifacts

- Windows process build 10.0.26200.
- NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94.
- Godot 4.7.2 stable .NET (`ed1daf0bf`), repository-local editor and export templates.
- Android Studio API 34 AVD `Pixel_3a_API_34_extension_level_7_x86_64`, serial
  `emulator-5554`, used only for development evidence.
- Clean-software fixture: QEMU 11.0.50/WHPX, guest `GOVOR-M8-VM`, Windows
  10.0.22000.0 AMD64; exact-image and VM limits are recorded above.
- Renderer: `apps/renderer/Builds/Windows/GovorRenderer.exe` (ignored build output).
- Debug APK: `apps/android/app/build/outputs/apk/debug/app-debug.apk`.
- Runtime logs/proof images: ignored files under `.cache/`.
- Inventory: `docs/benchmarks/local/latest-inventory.json` (inventory only, no performance claim).

## Next steps

Milestone 8 is complete. The next implementation work is Milestone 9 release acceptance on the
actual Windows target and a physical Android phone. Do not reuse the clean VM or Android emulator
to mark any M9 row passing.

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

## Exact next commands

```powershell
git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' status --short --branch
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi -NoDownload
./scripts/test.ps1 -Scope all
$env:UV_CACHE_DIR = Join-Path (Resolve-Path '.cache').Path 'uv-m8-final'
uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m8-final
$env:PRE_COMMIT_HOME = Join-Path (Resolve-Path '.cache').Path 'pre-commit-m8-resume'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = 'C:/Users/PC/Documents/GitHub/govor.ai'
uv run --frozen pre-commit run --all-files
./scripts/test.ps1 -Scope hardware
./scripts/benchmark.ps1 -Profile media-poc
./scripts/benchmark.ps1 -Profile local-ai
./scripts/benchmark.ps1 -Profile speech
./scripts/benchmark.ps1 -Profile renderer
./scripts/progress.ps1 -Action View
./scripts/progress.ps1 -Action Export -OutputPath '.cache/progress-export.json'
./scripts/progress.ps1 -Action DeleteAll -ConfirmDelete
./scripts/provider-credentials.ps1 -Action Status -Target '<credential-target>'
./scripts/test.ps1 -Scope speech
./scripts/benchmark.ps1 -Profile speech
./scripts/emulator-speech-smoke.ps1
./scripts/benchmark.ps1 -Profile local-ai
./scripts/build.ps1 -Target renderer
./scripts/renderer-smoke.ps1
./scripts/renderer-scene-smoke.ps1
./scripts/benchmark.ps1 -Profile renderer
./scripts/emulator-renderer-smoke.ps1
./scripts/dev.ps1 -Mode mock
./scripts/dev.ps1 -Mode local -PairingToken '<at-least-32-random-characters>'
```
