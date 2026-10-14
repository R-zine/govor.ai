# Current verified status

Last updated: 2026-10-14

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

## Verification ledger

| Command or check | Result | Evidence and limits |
| --- | --- | --- |
| `./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -NoDownload` | verified passing | Pinned local Python/.NET/Godot assets and locked dependencies restored without a download |
| `./scripts/test.ps1 -Scope all` | verified passing | 2026-10-12 final Milestone 6 run; Python, contracts, Kotlin, C#, media, Godot, and Android APK build |
| Python gate | verified passing | Ruff check/format, strict mypy, 121 tests, 85.56% branch coverage |
| Contract schema gate | verified passing | 22 schema/model/fixture tests include closed scene/avatar payloads and arbitrary-asset rejection |
| Kotlin gate | verified passing | 13 JVM contract/state-machine/timeline tests, including lesson-progress invariants and shared fixtures |
| Pure C# gate | verified passing | 8 .NET contract/allow-list tests, including scene/avatar validation and arbitrary-asset rejection |
| Media gate | verified passing | Strict mypy and 15 tests, including real aiortc loopback, flushed 48-to-16 kHz microphone resampling, renderer-buffer validation, and clean remote-track teardown |
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
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-m2-final` | verified passing | Final Milestone 2 audit: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-m3-final` | verified passing | Final Milestone 3 audit: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m4-final` | verified passing | Final Milestone 4 audit, including media and speech extras: no known vulnerabilities found; sandbox network denial was repeated with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m5-final` | verified passing | Final Milestone 5 audit: no known vulnerabilities found; the sandbox-denied query passed with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m6-final` | verified passing | Final Milestone 6 audit: no known vulnerabilities found; the sandbox-denied query passed with approved network access |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m7-final` | verified passing | No known vulnerabilities found |
| Pre-commit across all tracked/untracked sources | verified passing | Final Milestone 7 run passed JSON/YAML, line endings/whitespace, secret/size checks, Ruff, formatting, and contract tests |
| `./scripts/hardware-test.ps1` | Milestone 9 not executed | Ignores the active emulator and exits 2 because no physical phone is connected; this does not reopen Milestone 1 |
| Physical Android/Wi-Fi/media/soak bundle | Milestone 9 not executed | No suitable physical phone; mandatory before release, not a prerequisite for Milestones 2-8 |
| Remote GitHub Actions | not executed | Workflow includes the Godot renderer job, but the current milestone snapshot has not run remotely |

The final `./scripts/test.ps1 -Scope all` run passed on 2026-10-14: 140 Python tests at 86.18%
branch coverage, 22 dedicated contract tests, 13 Kotlin tests, 8 pure C# tests, 15 media tests, Godot
import/build/self-test, and the Android debug APK build. Pytest emitted the existing Starlette
`httpx` deprecation warning. Godot could not read the Windows root-certificate store and Android
analytics could not write outside the workspace; both are previously recorded managed-environment
warnings and every gate completed successfully.

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
- Renderer: `apps/renderer/Builds/Windows/GovorRenderer.exe` (ignored build output).
- Debug APK: `apps/android/app/build/outputs/apk/debug/app-debug.apk`.
- Runtime logs/proof images: ignored files under `.cache/`.
- Inventory: `docs/benchmarks/local/latest-inventory.json` (inventory only, no performance claim).

## Next steps

Milestone 7 is complete. The next implementation milestone is Milestone 8: package the Windows
host/renderer/local runtimes and Android app for reproducible installation, resolve all third-party
distribution obligations, add integrity-checked model delivery/update behavior, and verify clean
startup/shutdown without development tools.

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
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi -NoDownload
./scripts/test.ps1 -Scope all
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
