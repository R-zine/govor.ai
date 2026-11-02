# Current verified status

Last updated: 2026-11-02

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

Milestone 6 is complete. Its post-milestone presentation path now renders one of three selectable
CC0 skinned teachers over four packaged CC0 photographic backdrops; installed environment recipes
remain validated data-only primitives. The host maps lesson context to a closed scene specification
and maps actual speech PCM plus real-or-unavailable provider timing to bounded facial animation.
The selected Elena/Amira/Daniel profile also selects a matching female/male speech presentation.
The original four-scene, software-encoding, concurrent-inference, lip-sync, emulator, and later
Milestone 9 evidence remains recorded; ADR-0020 distinguishes the current visual build from that
historical accepted candidate.

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
target-performance, monitor-off, thermal, or bounded-stability criterion.

Milestone 9 is complete. On 2026-10-21 the target RTX 3060 Windows PC and a physical realme
RMX3939 completed the intended private-Wi-Fi release path with no `adb reverse`: pairing and stored
credential reuse, authenticated WSS and DTLS-SRTP, physical microphone return, hardware VP8
decode, lifecycle/network reconnect, portrait behavior, unfocused and monitor-off rendering,
resource/thermal measurement, and a historical 1,800-second transport/media run. That run
sustained 30.018 emitted fps and 29.726 unique Godot fps with zero reported video/audio packet
loss.

On 2026-10-22 the exact signed post-audit `0.1.11`/code 12 candidate passed a fresh 30-second
physical Wi-Fi benchmark, café completion through the phone microphone, Bulgarian help after
recognition ambiguity and return to English, persisted completion, clean package restart,
progress survival, IPA display, and bounded isolated-word playback. The product owner removed the fixed 30-minute
continuous-lesson/soak gate; recorded bounded interaction, stability, lifecycle, resources, and
clean teardown remain required. The historical long run remains supporting evidence only.

On 2026-10-22 the unlocked physical phone received a bounded local
Piper utterance saying `Какво означава order?` through hold-to-talk. Whisper displayed
`(speaking in foreign language)` rather than the phrase, but the teacher provided Bulgarian
guidance, returned to an English prompt, accepted the following bounded Kokoro English answer,
and advanced the same attempt. A second accepted English answer reached café 3/3; tapping
`Would` displayed `/wˈʊd/` and Bulgarian pronunciation help. This closes the explicit bilingual
flow with the recognition limitation recorded, not as a human-speech accuracy claim. The learner
then confirmed that the moving café/teacher was visible on the physical phone and that teacher
speech was audible, clear, and intelligible. The final suite, dependency audit, and all-files
pre-commit gates pass, so every Milestone 9 acceptance row is closed.

## Post-milestone photographic scenes and selectable teachers

On 2026-10-26 the blocky procedural teacher was removed. The renderer now packages Elena, Amira,
and Daniel as closed CC0 skinned GLBs generated from Ara 3D Gen/MakeHuman data. Each exposes 34
facial blend shapes including 14 speech visemes and contains no animation clip. The host
pre-connect screen has a persistent teacher menu; selection swaps the model before the lesson and
sends only the closed profile ID over `renderer.teacher_profile_selected` to shared host state.
The four built-in scene IDs now resolve to local CC0 photographic backdrops. Installed environment
recipes retain the ADR-0015 data-only primitive boundary.

Speech resolves the same profile at synthesis time. Elena and Amira use female Kokoro voices and
female eSpeak fallback variants; Daniel uses male Kokoro voices and the available male Bulgarian
Piper Dimitar voice. Because the installed Piper catalog has no female Bulgarian voice, female
profiles intentionally use local eSpeak `bg+f3` for Bulgarian rather than silently mismatching the
model. Optional cloud-compatible speech has independently configurable presentation voice names;
the application does not claim providers guarantee a speaker identity from those names.

Local verification completed so far:

- 46 focused host, speech, provider-router, and profile tests passed.
- Godot C# tests passed (10 tests), and Godot import/build/self-test passed before the final visual
  tuning; final all-scope verification is recorded below.
- The exported four-scene tour passed with four distinct 1280x720 photographic captures, profiles
  Elena/Amira/Daniel/Elena, open visemes in every capture, zero fallbacks, zero cache growth, a
  124-byte reported video-memory revisit delta, and 20 VP8 packets. Software VP8 encode p95 was
  9.7707 ms on the development RTX 3060 PC.
- A bounded exported-player UI proof visibly showed the `Teacher: Amira` menu on the opaque host
  pre-connect screen. It used a non-pairing placeholder image only to exercise layout; it is not QR
  compatibility, phone-camera, or physical-device evidence.
- `./scripts/build.ps1 -Target renderer` passed after the build command added Godot's explicit
  `--quit`; this prevents the headless export console from waiting after a completed package.
- `./scripts/test.ps1 -Scope all` passed on the final source: 291 Python tests at 85.27% coverage,
  Kotlin/JVM tests, 10 C# tests, 21 media tests, Godot import/build/self-test, and Android debug
  assembly. The only warnings were the existing Starlette `httpx` deprecation, inaccessible local
  pytest cache, and an offline NuGet vulnerability-index warning during the C# build.
- `uv run --frozen pip-audit` reported no known vulnerabilities.
- `uv run --frozen pre-commit run --all-files` passed every hygiene, secret/large-file, Ruff,
  contract, PowerShell, and affected-application test hook.

Asset source pages, authors, licenses, generator inputs, exact GLB/JPEG hashes, and the
animation-stripping build step are committed beside the assets. ADR-0020 records the current
architecture and voice mapping. This is software/development-machine evidence only. No new signed
package, physical phone, camera scan, acoustic judgment, hardware codec, or mixed-LAN acceptance
was executed, and the historical Milestone 9 record must not be read as acceptance of these new
visual assets.

### Signed 0.1.18 deployment amendment

On 2026-11-02 the current source was packaged as matching Windows and Android release 0.1.18
(Android version code 19). The package command passed Godot export, Android release lint/build,
APK Signature Scheme v2 verification with the established release certificate, embedded-runtime
imports, corresponding-source/prerequisite checks, and both packaged wrapper doctors. The signed
APK is 59,891,893 bytes with SHA-256
`b19c983697abc4282f65e4d8d9734696f34fe8b93b2b594fc579b5b12235fdb8`.

ADB identified the connected physical realme RMX3939 and updated the existing installation in
place from 0.1.14/code 15 to 0.1.18/code 19 with `adb install -r --no-streaming`; Android returned
`Success`. A subsequent package query reported the new version, and the resolved
`ai.govor.app/.MainActivity` completed a cold launch with `Status: ok`. The matching portable host
is `.cache/dist/govor.ai-0.1.18-windows-x64`; both `Setup-Govor.cmd --doctor-only` and
`Start-Govor.cmd --doctor-only` passed, and all required local models reported `ready`. The older
portable directory was retained as a rollback copy.

This deployment proves build, signature, update compatibility, package metadata, prerequisite/model
availability, and Android Activity startup. It did not start the host gateway or renderer, scan the
pairing QR, send media, exercise the selected teacher/voice on the phone, or test the mixed
Ethernet/Wi-Fi path. No server or audio was left running. Exact commands and results are in
`docs/benchmarks/2026-11-02-release-0.1.18-deployment.md`.

## Post-milestone JSON lesson catalog

On 2026-10-22 the four hard-coded Python lesson definitions and duplicated Android selector were
replaced by the strict JSON catalog in `assets/lesson-content`. Each lesson is a separate
versioned JSON file. The immutable domain loader rejects malformed, oversized, incomplete,
duplicate, or unsupported content; host startup additionally rejects any unknown closed scene
template. The original scenario IDs, exercise content, renderer scene IDs, and progress keys are
unchanged.

The authenticated control contract now includes `lesson.catalog.request` and `lesson.catalog`.
Android connects first, validates the host's ordered summary, then renders a scrollable dynamic
selector and starts only a returned scenario ID. A new JSON lesson was verified through host
catalog discovery, fake lesson startup, progress reporting, and reuse of the existing café scene
without Python/Kotlin/Godot content constants. Release packaging copies the source catalog to
`content/lessons`, the launcher passes that absolute directory to the host, and its doctor rejects
a package with no lesson files. ADR-0013 and `docs/development/lesson-content.md` define the
boundary and authoring procedure.

Verification from the source checkout:

- `./scripts/test.ps1 -Scope python`: verified passing; 184 tests plus Ruff, format, and mypy.
- `./scripts/test.ps1 -Scope contracts`: verified passing; 29 schema fixtures/tests.
- `./scripts/test.ps1 -Scope kotlin`: verified passing; 18 JVM tests across three suites.
- `./scripts/build.ps1 -Target android`: verified passing; debug APK built successfully.
- PowerShell parser check for both updated emulator smoke scripts: verified passing.
- `./scripts/test.ps1 -Scope all`: verified passing; Python, Kotlin, 8 C# tests, 21 media tests,
  Godot import/build/self-test, and Android debug assembly passed.
- `uv run --frozen pre-commit run --all-files`: verified passing after fetching the pinned hook
  environments; JSON/YAML, whitespace, line-ending, secret/size, Ruff, format, and contract hooks
  all passed.

No Android device was attached, so the updated selector and adjusted emulator smokes were not
executed on an emulator in this change. No release package or physical-device acceptance was
rerun; this does not alter or replace the recorded Milestone 9 evidence.

### Live host-side lesson import amendment

On 2026-10-22 the packaged Windows host gained `Manage-Lessons.cmd`, backed by a native Windows
file picker and a local launcher command. It accepts one JSON lesson or a ZIP containing multiple
JSON lessons, validates the entire bounded batch and combined catalog, rejects overwrites and
unknown scene templates, and publishes canonical files into `content/lessons`. ZIP entries are
read without extraction; traversal paths, encrypted/non-JSON entries, oversized compressed or
expanded input, malformed definitions, and duplicate IDs are rejected. A failed batch leaves the
installed files unchanged.

The control host now watches the local lesson directory. It swaps only a fully valid immutable
catalog and pushes the ordered `lesson.catalog` summary on every connected authenticated control
socket. Android applies a pushed catalog without interrupting an active session; each active
lesson retains its start-time catalog/service snapshot and a later lesson uses the new one. An
invalid out-of-band edit retains the previous catalog and changes `/health`
`lesson_catalog_status` to `reload_error`. No LAN upload or administration endpoint was added.

Verification for this amendment:

- Focused Ruff plus launcher/domain/host/distribution tests: verified passing, 48 tests including
  the real launcher command, publish rollback, and excessive ZIP-entry rejection.
- `./scripts/test.ps1 -Scope python`: verified passing as part of the final all-scope run; 200
  tests, Ruff, format, strict mypy, and 85.28% combined coverage.
- `./scripts/test.ps1 -Scope kotlin`: verified passing; 18 JVM tests across three suites.
- `./scripts/build.ps1 -Target android`: verified passing. The Kotlin daemon could not create its
  user-profile marker in the managed environment, then Gradle's supported in-process fallback
  compiled and assembled the debug APK successfully.
- `Import-Lessons.ps1` PowerShell parser check: verified passing.
- `./scripts/test.ps1 -Scope all`: verified passing; 200 Python tests at 85.28% combined coverage,
  Kotlin tests, 8 C# tests, 21 media tests, Godot import/build/self-test, and Android debug assembly.
- `uv run --frozen pre-commit run --all-files`: verified passing; JSON/YAML, line-ending,
  whitespace, secret/size, Ruff, format, and contract hooks all passed.
- The live host test imported a lesson while a control WebSocket remained connected, received the
  unsolicited replacement catalog, and started that imported lesson on the same connection.
- The native file-picker dialog and resulting Android selector were not manually exercised in this
  run. No emulator/device was attached, and no release package or physical acceptance was rerun.

### Local LLM lesson creator

On 2026-10-23 the packaged Windows host gained `Create-Lesson.cmd` and a native form for a required
lesson topic plus optional content difficulty, visual environment, and one-to-eight exercise
length. Omitted settings resolve deterministically to intermediate difficulty, five exercises, and
an allow-listed environment selected from topic keywords or a stable hash. These choices require
no model call.

The existing loopback-only Qwen/llama.cpp backend generates bounded teaching content through the
new closed `local-ai-lesson-content` schema. The model has no fields for file paths,
scenario/exercise IDs, display order, schema version, scene IDs, application commands, or renderer
assets, and generated prose is never interpreted as one. Application code adds the structural
fields, validates the assembled version 1 lesson, and publishes it
through the same locked additive importer. The existing watcher therefore supplies the live
Android catalog update while preserving any active lesson snapshot. ADR-0014 records the decision.

Verification to date:

- `./scripts/test.ps1 -Scope contracts`: verified passing; 32 schema/fixture tests including valid
  generated content and rejection of an injected application command.
- `./scripts/test.ps1 -Scope python`: verified passing; final focused run had 225 tests at 85.46%
  combined branch
  coverage plus Ruff, format, and strict mypy. Tests cover deterministic defaults, explicit
  settings, output bounds, loopback enforcement, retry bounds, exact exercise count, unique
  additive IDs, complete lesson validation, importer publication, launcher dispatch, and package
  entrypoints.
- `./scripts/check-powershell-syntax.ps1 -Paths distribution/windows/Create-Lesson.ps1`: verified
  passing.
- A bounded real Qwen3 4B Q4_K_M/llama.cpp smoke generated one beginner airport exercise from
  `Practice asking for help after a flight is delayed`, produced a valid canonical lesson through
  the actual launcher/provider/importer path, and reported the expected resolved settings. It used
  an isolated ignored catalog; the generated smoke directory was removed and port 8767 was no
  longer listening afterward.
- `./scripts/test.ps1 -Scope all`: verified passing; 224 Python tests at 85.44% combined coverage,
  Kotlin/JVM tests, 8 C# tests, 21 real media tests, Godot import/build/self-test, and Android debug
  assembly all passed. The Godot build emitted only the existing inability to query NuGet's online
  vulnerability feed in the restricted environment.
- `uv run --frozen pre-commit run --all-files`: verified passing; JSON/YAML, line endings,
  whitespace, secret/size checks, Ruff, format, 32 contract tests, PowerShell syntax, and the
  path-selected complete software gate all passed.
- The final full-catalog preflight guard was followed by the 225-test Python run above and
  `pre-commit run --files` on its implementation, regression test, and this handoff; every selected
  hook passed.

The native form itself, a rebuilt portable package, and a live connected Android catalog push were
not manually exercised in this maintenance run. The underlying importer-to-live-watcher path was
already directly verified in the preceding import amendment, but that prior evidence is not a
claim that this new form was clicked. Completed Milestone 8/9 VM and physical acceptance were not
rerun because this feature changes neither Android, media, rendering, network gateways, nor device
behavior.

### Patchable procedural environment bundles

On 2026-10-23 the four built-in Godot environments were extended with additive, local data-only
environment bundles. `Manage-Environments.cmd` opens a native Windows ZIP picker. The launcher
reads one to 32 JSON entries without extracting paths, rejects encrypted/non-JSON/traversal or
oversized input, protects built-in and installed IDs, validates the complete result, and publishes
canonical recipes under `content/environments` using an import lock. Failed batches roll back.

The version 1 recipe has closed camera/lighting/transition and box/cylinder/sphere choices,
bounded finite dimensions/colors/transforms, and at most 64 objects. It has no field for a Godot
scene/resource, model, texture, shader, path, URL, script, command, or assembly. Python, JSON
Schema, and C# enforce the translated renderer boundary. Godot constructs the primitives in memory
through the existing cache; it never opens the bundle.

The host watches the environment directory and swaps only a complete valid immutable planner
snapshot. Invalid edits retain the prior planner and set `environment_catalog_status` to
`reload_error`. Lesson imports and generated lessons validate against installed environments, and
the creator form obtains current display names from the launcher. A valid addition is therefore
usable by a later lesson without restarting the host or renderer. ADR-0015 and
`docs/development/environment-content.md` define the format and authoring path.

Verification to date:

- Focused scene-planner, contract, launcher, distribution, and host-registry tests: verified
  passing. The live host test installed an environment, observed the planner refresh, imported a
  referencing lesson, and started it on the same control connection; its renderer command carried
  the custom primitive.
- `./scripts/test.ps1 -Scope contracts`: verified passing, 36 schema/model/fixture tests.
- `./scripts/test.ps1 -Scope python`: verified passing, 241 tests at 85.11% combined branch
  coverage plus Ruff, format, and strict mypy.
- `./scripts/test.ps1 -Scope csharp`: verified passing, 9 tests.
- `./scripts/test.ps1 -Scope godot`: verified passing; Godot imported the project, compiled the
  C# consumer, preserved custom sphere dimensions, and printed `GOVOR_GODOT_SELF_TEST_PASS`.
- PowerShell parsing for `Import-Environments.ps1`, dynamic `Create-Lesson.ps1`, and
  `package.ps1`: verified passing.
- `./scripts/test.ps1 -Scope all`: verified passing; the Python results above, Kotlin/JVM tests,
  9 C# tests, 21 real media tests, Godot import/build/self-test, and Android debug assembly passed.
  Godot emitted only the existing restricted-environment certificate-store/NuGet feed warnings.
- `uv run --frozen pip-audit`: verified passing; no known vulnerabilities found.
- `uv run --frozen pre-commit run --all-files`: verified passing; JSON/YAML, endings,
  whitespace, secret/size, Ruff/format, 36 contract tests, PowerShell syntax, and the affected-app
  software gate all passed. Final selected-file reruns also passed after the documentation and
  ASCII-safe environment-list JSON output edits.
- No portable release package, Windows picker click, Android/emulator run, or physical-device run
  has been executed for this maintenance feature. Prior milestone hardware evidence is not reused
  as proof of the new UI.

### Path-aware pre-commit software gate

On 2026-10-23 pre-commit gained a staged-path dispatcher in
`scripts/pre-commit-tests.ps1`. Host, launcher, domain, progress, and ordinary shared Python changes
select the complete Python lint/format/mypy/test/coverage gate. Media and speech select their
dedicated typed test gates. Android changes select JVM tests and debug APK compilation. Renderer
changes select the bounded Godot import/build/self-test gate. C# contract changes select C# tests
and the renderer consumer gate. Shared wire contracts, dependency/lock files, CI workflows, and
test infrastructure select `Scope all`. Multiple component selections are de-duplicated and run in
a stable order; documentation-only changes skip software suites.

The existing JSON/YAML, line-ending, whitespace, secret, large-file, Ruff, formatting, and contract
checks remain. A new local hook parses every changed PowerShell file before affected tests run.
Neither hook ever selects physical-device, acoustic, performance, network-acceptance, or soak
commands. The separate Linux pre-commit CI job skips the two Windows-local hooks because the
dedicated Windows/Android/renderer CI jobs already execute their software suites.

Verification:

- `uv run --frozen pre-commit validate-config`: verified passing.
- Dispatcher mapping and PowerShell accept/reject integration tests: 9 verified passing.
- Repository-wide `*.ps1` parser run: verified passing.
- `uv run --frozen pre-commit run affected-tests --files scripts/pre-commit-tests.ps1`: verified
  passing; the infrastructure path selected and completed the full software suite.
- `./scripts/test.ps1 -Scope all`: verified passing on the final hook implementation; 209 Python
  tests at 85.28% combined coverage, Kotlin, 8 C# tests, 21 media tests, Godot
  import/build/self-test, and Android debug assembly all passed.
- `uv run --frozen pre-commit run --all-files`: verified passing with every hygiene hook, the new
  PowerShell parser, and the affected-tests full-suite selection.

ADR-0003 now selects Godot 4.7.2 .NET as the only renderer. The earlier proof from the proprietary
engine was removed completely, including source, project metadata, build scripts, and dependencies.
Godot import, C# compilation, self-test, Windows export, local runtime, non-black shared-memory
video, non-silent application PCM, and emulator delivery have all executed successfully. The
current synchronous `SubViewport.GetTexture().GetImage()` readback is accepted because the
mandatory Milestone 9 target-hardware cadence/resource measurements passed. Future target or
performance regressions may still require revisiting it.

## Current implementation

- `apps/renderer` is a Godot 4.7.2 .NET project with three selectable CC0 facial teachers, four
  built-in CC0 photographic backdrops plus validated data-only procedural environments, a
  dedicated 1280x720 `SubViewport`, and the bounded media-test tone.
- `packages/scene_planner` owns built-in and installed immutable scene recipes plus actual-PCM/
  provider-timing avatar plans without depending on Godot, FastAPI, Android, or providers.
- The version 1 renderer contract accepts bounded environment IDs, closed presets, and exactly one
  built-in asset or bounded procedural primitive per object. It rejects arbitrary paths, URLs,
  scripts, resources, and unknown fields.
- Godot caches packaged backdrop textures and procedural mesh/material resources, queues replaced
  scene trees for cleanup, supplies a predictable internal primitive fallback, and writes no
  generated 3D files at runtime.
- Elena, Amira, and Daniel share bounded idle/blink and state expression behavior. PCM energy
  drives mouth opening; their facial rigs provide 34 blend shapes including 14 speech visemes,
  which are used only when real provider phoneme timing exists.
- The tone stops automatically. Runtime smokes are muted by default; the single supervised
  audible check also stopped after two seconds.
- Godot publishes top-to-bottom RGBA through two alternating latest-frame slots in a Windows named
  mapping and PCM into a bounded 64-block ring. The mappings are process-local and expose no LAN
  listener.
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
- `assets/lesson-content` defines the café, supermarket, airport, and home lessons as strict JSON;
  `packages/domain` loads them into immutable definitions and owns the pure `TeachingEngine`. The
  LLM may classify intent but cannot award success or choose progression.
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
- Android requests the bounded startup lesson catalog, then `session.start` accepts a returned
  scenario ID, English accent, and review preference. Each host-generated `teacher.turn` includes
  an additive progress snapshot. The host sends completed session teardown only after the final
  audio playback acknowledgement.
- Android renders the host-provided lesson list, GB/US selection, a spaced-review toggle,
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
| `./scripts/test.ps1 -Scope all` | verified passing | 2026-10-21 M9 source run passed all Python/contracts/Kotlin/C#/media/Godot gates and the Android debug build; the first attempt exposed only Ruff import ordering, which was corrected before the from-start pass |
| M9 Kotlin lifecycle policy | verified passing | Four new pure tests cover single foreground reconnect, explicit-disconnect suppression, unused policy, and network retry; total Kotlin gate is 17 tests |
| M9 media gate | verified passing | Strict mypy and 21 tests cover the version 2 two-slot bridge, stable header/inactive-slot publication, bounded phase wait, metrics, RTP state, and authenticated signaling |
| `./scripts/hardware-test.ps1 -DurationSeconds 30 ...` | verified passing on physical target | Exact 0.1.10 candidate: 30.380 seconds, 30.052 unique Godot fps, +1,507 physical microphone frames, zero reported RTP loss, connected DTLS |
| `./scripts/hardware-test.ps1 -DurationSeconds 1800 ...` | verified passing as transport soak | Physical intended-Wi-Fi run: 1,800.065 seconds, 30.018 emitted fps, 29.726 unique Godot fps, +89,863 microphone frames, zero reported RTP loss, bounded measured resources; not a continuous interactive lesson |
| Physical lifecycle/network recovery | verified passing | Background/foreground, Wi-Fi loss/recovery, explicit disconnect/reconnect, stored-credential reuse, and state preservation passed on the real phone; delayed ICE transition was observed and recovered |
| Hardware codec selection/fallback | verified with fallback | Android resource manager reported hardware `c2.unisoc.vp8.decoder`; Windows metrics reported VP8 software encoding (`windows_hardware_video_encoding=false`) |
| Monitor-off/unfocused renderer | verified passing | Renderer/media/microphone/DTLS counters advanced with the application unfocused and monitor off; bounded wake restored the display after an unresponsive unrelated window blocked the first helper |
| Human phone picture/speech confirmation | verified passing | On 2026-10-22 the learner confirmed that the moving café/teacher was visible and teacher speech was audible, clear, and intelligible on the physical phone |
| Fixed-duration continuous lesson | removed from acceptance on 2026-10-22 | The historical 1,800-second transport run waited for learner input and is not relabeled as interactive; no fixed-duration lesson or soak is now required |
| First M9 dependency audit | verified failing then remediated | Found certifi `PYSEC-2026-4320` and virtualenv `GHSA-vxj4-q4g9-crj7`; pins/lock were updated to certifi 2026.10.19 and virtualenv 21.14.12 |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m9-final` | verified passing | Post-remediation locked graph: no known vulnerabilities found |
| M9 pre-commit across all sources | verified passing | Final post-documentation run passed JSON/YAML, line endings/whitespace, secret/size checks, Ruff, format, and 26 contract tests |
| `./scripts/package.ps1 -Version 0.1.11 -VersionCode 12 -NoArchive ...` | verified passing | Post-audit Godot export, signed APK build/signature, dependency/source staging, imports, prerequisites, and wrapper doctor smokes passed; APK SHA-256 `94662d516bfff260b3276522142bb7ce34a995f03400011df914940c10b87e2a` |
| Exact 0.1.11 physical smoke | blocked | APK installed, but the handset returned to its PIN screen before connection; no PIN was requested or guessed |
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
fixtures and remain evaluation inputs for future teaching/speech work. The separate physical-phone,
Wi-Fi, acoustics, codecs, concurrent target load, thermals, and bounded-stability criteria later
passed in Milestone 9.

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

The API 34 UI check is emulator development evidence only. At this checkpoint no live human lesson
or physical phone, Wi-Fi, codec, acoustic, target-load, thermal, or bounded-stability acceptance
had run. Those did not block Milestone 5 and later passed separately in Milestone 9. This handoff
is the required focused Milestone 5 commit.

## Milestone 6 acceptance and handoff

> Historical gate: this table records the original procedural Milestone 6 candidate. ADR-0020 and
> the post-milestone section above describe the current photographic/selectable-teacher build; no
> physical evidence from this table is transferred to the replacement assets.

| Acceptance criterion | Status | Direct evidence |
| --- | --- | --- |
| Teacher visible in streamed 3D environment | verified passing with emulator limit | Four local 1280x720 captures visibly contain the original stylized teacher; renderer-originated non-black video reached native Android at 30 fps with no drops in the final short interval. |
| Speaking animation corresponds to teacher audio | verified passing | The host extracts energy from actual PCM sample positions. Real Kokoro delivered 51 energy samples and 23 provider-timed visemes to Godot for a 2,038,666 µs utterance. |
| At least four environments assemble | verified passing | Exported Godot captured distinct café, supermarket, airport, and home frames with zero fallbacks. |
| Environment responds to lesson context | verified passing | Host integration maps selected scenario to its deterministic scene; the emulator smokes required the café scene marker, and planner tests cover every scenario. |
| Invalid scene specifications rejected | verified passing | Python/JSON Schema/C# validation rejects unknown IDs, bounds, extra fields, and an explicit `../../downloaded-model.glb` fixture. |
| Missing assets have predictable fallbacks | verified passing | Godot self-test invokes an internal unknown catalog item and verifies the named magenta fallback; untrusted unknown wire IDs are rejected earlier. |
| Scene changes do not leak significant GPU memory | verified passing with bounded scope | After all four scenes, a cached café revisit added zero cached resources and zero Godot-reported video-memory bytes. This short run is not a long-duration claim. |
| Runtime scene data stays in memory | verified passing | Procedural scene nodes/resources are created in memory; the tour writes proof PNGs only in explicit benchmark mode, not generated 3D scene files. |
| Rendering usable beside local inference | verified passing on development PC | Renderer tour/encoding overlapped two Qwen3 4B requests; frame p95 was 33.459 ms at the 30 fps target. |
| Required performance measurements | verified passing with limits | Scene builds 0.243–1.210 ms; transitions 370.550–376.994 ms; cached revisit 0.436 ms; avatar 27.826 µs/frame; software VP8 p95 6.640 ms; memory figures recorded in the dated benchmark. |

Implementation and boundary decisions are recorded in ADR-0009. Exact commands, transient
failures, artifacts, metrics, and limits are in
`docs/benchmarks/2026-10-12-avatar-scenes-and-renderer-performance.md`. No new third-party
dependency or downloaded renderer asset was added.

The real-alignment emulator run proves the control/timing path, not physical display quality or
acoustics. The cache/video-memory revisit is a bounded regression check, not a long-duration leak test.
Physical phone/Wi-Fi/audio, target-machine resource behavior, lifecycle, monitor-off, thermals, and
bounded stability were deferred to and later passed in Milestone 9; the accepted Windows codec
path remained software VP8 encoding. This handoff is the required focused Milestone 6 commit.

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
suite, locked dependency audit, and all-files pre-commit gate passed. Milestone 9 began on
2026-10-21. Its new physical evidence does not alter or retroactively expand the M8 software-only
result.

## Milestone 9 acceptance and handoff (complete)

| Acceptance criterion | Status | Direct evidence and limit |
| --- | --- | --- |
| Physical phone on intended Wi-Fi | verified passing | realme RMX3939 on `A1_B436` reached the target PC's release gateways with no `adb reverse`; Windows network profile was Private |
| Continuously rendered PC scene reaches phone | verified passing | 53,508 unique Godot frames over 1,800.065 seconds, hardware decoder activity, and the learner's 2026-10-22 confirmation that the moving café/teacher was visible on the phone |
| Teacher audio on phone | verified passing | Phone playback completion advanced the lesson while Windows playback was muted; the learner confirmed that teacher speech was audible, clear, and intelligible on the handset |
| Phone microphone reaches PC | verified passing | +1,532 physical 48 kHz microphone frames in the exact-candidate smoke; bounded acoustic hold-to-talk turns completed café 3/3 |
| No PC speaker/microphone dependency | verified architecturally/partially physically | Muted Windows playback did not stop phone lesson playback; capture opens only the phone WebRTC track and no PC microphone. A physical PC-microphone-disable action was not executed |
| Pairing, WSS, DTLS-SRTP, firewall/private LAN | verified passing on measured candidate | Initial pairing, stored credential reuse, authenticated WSS, connected DTLS, and Private-profile Wi-Fi passed; public-internet deployment remains forbidden |
| Lifecycle/interruption/reconnect/state | verified passing | Background/foreground, Wi-Fi loss/recovery, explicit disconnect/reconnect, and same-process state preservation passed; one deliberate second-Activity harness misuse is excluded |
| Codec selection/fallback | verified with explicit fallback | Android hardware `c2.unisoc.vp8.decoder`; Windows VP8 software encoding met cadence, and no hardware-encode claim is made |
| Unfocused/monitor-off/idle-awake | verified passing | Renderer/media/mic/DTLS counters advanced while unfocused and through a monitor-off interval |
| Orientation/acoustics/latency/loss/resources/thermals/cadence | verified passing | Portrait lock, latency/loss/resources/thermals/cadence were measured; the learner confirmed handset speech audibility and intelligibility |
| Bounded stability | verified passing | Exact-candidate 30.609-second run had advancing media/microphone counters, zero reported RTP loss, and bounded resources; the historical 1,800.065-second transport run adds longer supporting evidence but is not a release gate |
| Final local-first café scenario and restart | verified passing with recorded recognition limit | Physical microphone turns reached café 3/3, saved progress, survived package restart, retained completion, displayed IPA/help, and played bounded isolated-word audio. A later exact-candidate attempt sent the explicit local Piper phrase `Какво означава order?` acoustically through the physical phone microphone; Whisper reduced it to `(speaking in foreign language)`, the teacher supplied Bulgarian guidance and returned to English, recognized the following English answer, and advanced the same lesson to 3/3. This is end-to-end bilingual-flow evidence, not a human-speech accuracy claim |
| Full automated suite/audit/pre-commit | verified passing | Final run passed: 169 Python at 85.51% branch coverage, 26 contracts, 17 Kotlin, 8 C#, 21 media, Godot import/build/self-test, and Android debug build; locked audit reported no known vulnerabilities and every all-files pre-commit hook passed |
| Exact post-audit release | verified passing | Signed 0.1.11/code 12 passed the physical Wi-Fi benchmark, full café/restart path, stored-credential reconnect, and clean teardown |

Implementation and decisions:

- Android lifecycle recovery is Activity/ViewModel-owned and driven by a pure policy with four JVM
  tests. Explicit disconnect remains authoritative; release retries never reuse a one-time pairing
  code.
- Renderer video mapping version 2 alternates two full RGBA slots and commits only the inactive
  slot. The reader checks a stable header and the aiortc track may await a publication for 20 ms,
  eliminating measured phase aliasing without queue growth.
- Loopback-only metrics and the physical benchmark measure actual session/RTP/renderer/microphone
  state. No diagnostics listener was exposed on the LAN.
- Android hardware VP8 decode is accepted. aiortc software VP8 encoding is the recorded Windows
  fallback because it sustained the target cadence; hardware encoding is not claimed.
- The 2026-10-22 product decision removed fixed-duration lesson/soak acceptance. The historical
  1,800-second record remains supporting transport evidence and is not called interactive.

Implementation files changed for M9 are the Android Activity/ViewModel and new lifecycle policy
plus tests; the Godot bridge protocol/publisher/self-test; media app, peer, reader, and tests; and
the hardware/benchmark scripts. The dependency remediation also changes `pyproject.toml`,
`uv.lock`, and `THIRD_PARTY_LICENSES.md`. Architecture, ADR, roadmap, hardware ledger, renderer
README, and this handoff were updated together. Exact paths and measurements are listed in
`docs/benchmarks/2026-10-21-m9-physical-release-acceptance.md`.

Meaningful commands and results:

- `./scripts/test.ps1 -Scope all`: the final post-documentation run passed with 169 Python, 26
  contracts, 17 Kotlin, 8 C#, and 21 media tests plus Godot and Android build gates.
- `./scripts/package.ps1 -Version 0.1.10 -VersionCode 11 -NoArchive ...`: passed and produced the
  measured candidate.
- `./scripts/hardware-test.ps1 -DurationSeconds 30 ...`: passed on exact 0.1.11 with 30.482 emitted
  fps, 29.959 unique Godot fps, +1,532 microphone frames, zero reported RTP loss, and connected
  DTLS.
- `./scripts/hardware-test.ps1 -DurationSeconds 1800 ...`: passed the transport/media soak with
  30.018 emitted fps, 29.726 unique Godot fps, zero reported RTP loss, and +89,863 microphone
  frames.
- First M9 `pip-audit`: failed on certifi/virtualenv advisories. Targeted lock updates followed;
  repeat audit passed with no known vulnerabilities.
- `./scripts/package.ps1 -Version 0.1.11 -VersionCode 12 -NoArchive ...`: passed. One launcher
  attempt hit transient Windows asyncio WinError 64 during socket accept; a retry started all
  required services and passed packaged-Python TLS health. After the phone was unlocked, the
  exact package passed physical connection, lesson, restart, and pronunciation/playback checks.
- Exact 0.1.11 physical follow-up on 2026-10-22: stored-credential Wi-Fi reconnect passed after
  trimming two accidental trailing spaces from the certificate field. A repeated Bulgarian
  acoustic attempt was mis-transcribed as Korean text; a clean single utterance was classified as
  foreign language and produced Bulgarian guidance plus an English prompt. The next Kokoro phrase
  was recognized as `Would you like a coffee, please?`, advanced to 2/3, and exposed
  `Would /wˈʊd/`; `That is all, thank you` was recognized and advanced to 3/3. Transient
  recoverable lesson states recovered through **Retry lesson**. A Windows SAPI job failed to
  initialize and supplied no speech; it is recorded as a failed attempt, not evidence.
- `uv run --frozen pre-commit run --all-files`: the post-follow-up documentation run passed every
  configured hook, including Ruff and 26 contract tests.
- All services, Godot, llama.cpp, and the Android app were stopped. Stay-awake and rotation were
  restored; no tone is active.

The learner confirmed the moving phone picture and clear, intelligible phone speech on
2026-10-22. The release package, physical app, services, and every temporary generated utterance
were stopped or deleted after the bounded follow-up. Milestone 9 has no remaining blocker and is
closed by this focused handoff commit.

## Post-milestone signed application patch handoff

The 2026-10-23 maintenance implementation is complete at the software/package boundary. It adds a
dedicated ACL-protected RSA-3072 application-update identity, `config/release.json`, a signed
version 1 `.govorpatch` manifest, a developer diff/signing command, and packaged
`Apply-Govor-Patch.cmd`/`.ps1` picker/verifier. The host transaction authenticates the manifest,
requires the exact source release and old hashes, validates all paths/members/sizes/new hashes,
stages before mutation, commits the target release marker last, and restores earlier operations if
a later write fails. Its bootstrap and public trust key are intentionally non-patchable. Unlisted
files and `%LOCALAPPDATA%` models/progress/security state are preserved.

An optional Android APK is bound into the same signed manifest and retained under the per-user
updates directory. Actual phone installation remains a separate explicit platform action: the user
must copy/open the APK and approve Android's update dialog. No ADB, silent install, unknown-source
bypass, or LAN update endpoint was added. No physical phone update was executed in this change, so
the generated/staged APK is not Android runtime evidence. Existing 0.1.11 installations need one
full updater-capable package replacement before incremental patches can be used. ADR-0016 records
the decision and `docs/development/application-patches.md` records authoring commands.

Verification and failures:

- `./scripts/initialize-update-signing.ps1`: passed, then a repeat retained the same key. The
  ignored private/public pair is RSA-3072 and Python confirmed the public half matches; private key
  bytes were not printed or packaged.
- Focused patch tests: 9 passed. They cover manifest/payload authentication, key mismatch, protected
  bootstrap/trust files, Android signer continuity, the PowerShell authoring wrapper, a real
  add/replace/delete/APK transaction, preservation of an unlisted lesson, tamper rejection before
  mutation, and automatic rollback after a deliberately late filesystem failure.
- The first sandboxed package attempt stalled after successful Godot export because the sandbox
  denied certificate-store access; it was interrupted and not counted. Outside that restriction,
  the first package attempt found the staged import smoke still used repository-relative lesson
  paths. `scripts/package.ps1` was corrected to map staged lesson/environment directories.
- The first full suite after adding the authoring module ran 254 tests successfully but failed the
  85% runtime coverage gate at 83.93%. The developer-only patch authoring module and shipped
  PowerShell transaction now have dedicated integration tests and are classified with the existing
  Windows launcher/orchestration coverage exclusions; runtime coverage remains enforced.
- Final `./scripts/test.ps1 -Scope all`: passed. It ran 254 Python/contract/integration tests at
  85.11% application-runtime coverage, Kotlin tests, 9 C# tests, 21 real media tests, Godot
  import/C# build/headless self-test, and Android debug assembly.
- Final `uv run --frozen pip-audit`: passed with no known vulnerabilities after the expected
  sandbox-network failure was repeated with network access.
- Final `uv run --frozen pre-commit run --all-files`: passed every configured hook, including
  private-key detection, JSON contracts, PowerShell parsing, Ruff, and the affected full suite.
  A later documentation-only repeat could not read the pre-commit environment created outside the
  sandbox when run inside it; repeating at the same access boundary passed.
- PowerShell syntax passed for the updater, both signing scripts, patch creator, and packager.
- Final `./scripts/package.ps1 -Version 0.1.12 -VersionCode 13 -NoArchive`: passed outside the
  certificate-store sandbox. Godot export, stable signed APK verification, embedded runtime/source
  staging, imports, doctor, and all three Windows wrapper doctor smokes passed.
- The final ignored candidate directory contains the updater, public key, and version metadata but
  no `.secrets` directory/private exponent. Its updater SHA-256 is
  `4b99a01fb576df5f0406d8f071f98a7549de6d18d97c584cf888625dd69e7fd3`.
- Candidate APK `.cache/dist/govor.ai-0.1.12-android-release.apk` is 55,425,173 bytes with SHA-256
  `bedb0cf2cecdf67773d368db819ce0fea1d2edf159ead8ebb80e5b0dd714d4ab`; apksigner verified its
  stable certificate SHA-256
  `b7022cb8bbcc0a4828cf73e5ef958e1b431ccce697020577c4a502a66ec59843`.

Acceptance status:

| Criterion | Status | Evidence / limitation |
| --- | --- | --- |
| Exact-base signed host patch | verified passing | Real PowerShell add/replace/delete transaction from a generated RSA-signed patch |
| Tamper/wrong-key/unsafe bootstrap rejection | verified passing | Python signature/integrity tests plus packaged PowerShell payload-tamper rejection |
| Partial-write rollback | verified passing | Late parent-file collision restored replace/delete/add operations and retained source release metadata |
| Preserve unlisted local content/per-user state | verified passing | Unlisted lesson survived; updater operates only on signed install-root paths and stages below the update directory |
| Optional Android APK binding/staging | verified passing | APK metadata/hash is signed and the Windows transaction retained exact fixture bytes |
| Android update accepted/runs on phone | not executed | Requires explicit transfer/open/install on a physical phone; no claim is inferred from package creation |
| Pre-updater 0.1.11 incremental upgrade | not supported by design | Install one full updater-capable release first |

Exact next release workflow:

```powershell
./scripts/package.ps1 -Version '<next-version>' -VersionCode '<higher-code>' -NoArchive
./scripts/create-application-patch.ps1 `
  -BasePackagePath '<retained-updater-capable-base-directory>' `
  -TargetPackagePath '<new-package-directory>' `
  -AndroidApkPath '<new-signed-release.apk>' `
  -OutputPath '<base-to-target.govorpatch>'
```

Before sending a real patch, apply it to an exact copy of the supported base and run the resulting
host. When it contains Android changes, install that APK on the intended test phone and record the
platform result separately. No milestone was reopened. The completed environment/application patch
work is recorded in focused commit `f293cac`.

## Post-milestone Android loudspeaker default

The 2026-10-23 Android maintenance change defaults an active lesson to the phone's built-in main
loudspeaker rather than the quiet call earpiece. The WebRTC session captures the pre-session audio
mode and route, selects `TYPE_BUILTIN_SPEAKER` through Android's communication-device API on API
31+, and uses the speakerphone compatibility API on supported API 26-30 devices. It reasserts the
route when the peer connects and when the remote audio track arrives. Disconnect, background
teardown, signaling/media failure, and release restore the captured route and audio mode. The
normal `MODIFY_AUDIO_SETTINGS` manifest permission permits routing but does not change volume.

Verification and limits:

- `./scripts/test.ps1 -Scope kotlin`: verified passing; 22 JVM tests include four new route-
  lifecycle tests for repeated activation, reconnect recapture, failed-selection retry, and
  capture failure. The managed environment denied the external Kotlin daemon marker, and Gradle's
  supported in-process fallback completed successfully.
- `./scripts/build.ps1 -Target android`: verified passing; API 34 compilation and debug APK
  assembly succeeded. The resulting APK is 58,803,854 bytes.
- Final selected `uv run --frozen pre-commit run --files ...`: verified passing; hygiene, JSON
  contracts, PowerShell syntax, and the path-aware complete software gate passed.
- The first two `0.1.13` signed-package attempts reached release compilation but the workspace-
  local Gradle transform cache denied Java access to one readable AndroidX JAR. Repeating the
  exact build with the existing user Gradle cache and `-GradleOffline` passed: Godot export,
  signed APK verification, embedded runtime/source staging, imports, prerequisites, and all
  packaged wrapper doctors completed.
- The first real package-to-package patch-authoring attempt exposed that the new path allow-list
  did not admit existing package-owned `libstdc++`, eSpeak `!v`, and space-containing filenames.
  Authoring stopped before producing an archive. Python, JSON Schema, and PowerShell validation
  now admit only those additional bounded characters while continuing to reject traversal,
  separators/drive syntax, trailing-dot/space aliases, and Windows reserved device names. The
  focused patch/contract run passed 48 tests; the official Python gate passed 258 tests at 85.11%
  coverage with strict mypy, and the contract gate passed 39 tests.
- `./scripts/create-application-patch.ps1` then produced the signed 33,629,262-byte
  `.cache/dist/govor.ai-0.1.12-to-0.1.13.govorpatch`, SHA-256
  `00808e65312027857f06090c5e86f9a20dab69110062bd01418c4b1c0b4b4dff`, with 536 host
  operations and the target APK. The installed 0.1.12 updater applied it to a disposable exact
  base copy, committed version 0.1.13, matched the target Android source hashes, and staged an
  exact APK hash. The disposable host/data copies were removed afterward.
- The signed `0.1.13`/code-14 APK is 55,441,597 bytes with SHA-256
  `e43ab76a2d638a301bb404468b5a859915de3b950d716dde4a5903bfb1fffd1e` and the retained signer
  SHA-256 `b7022cb8bbcc0a4828cf73e5ef958e1b431ccce697020577c4a502a66ec59843`.
- The `0.1.13` incremental target deliberately retains the protected 0.1.12 updater bootstrap;
  the broader package-filename compatibility change cannot replace that bootstrap through a
  patch and must enter the next full release. The audio change itself uses only paths accepted by
  0.1.12 and its real transaction passed.
- Elevated `adb devices -l`: no Android device or emulator was attached. Actual earpiece-versus-
  loudspeaker routing, volume, and acoustics are therefore **not executed** for this maintenance
  change and are not inferred from compilation or the earlier Milestone 9 release evidence.
- No emulator run or physical-phone installation was executed. Before distribution, a direct
  handset check should install the staged code-14 APK and confirm main-loudspeaker playback plus
  route restoration after disconnect/background. This handoff is part of the feature's focused
  commit.

## Post-milestone contextual Android UI

The 2026-10-24 Android maintenance change replaces the single persistent control overlay with a
native Jetpack Compose Material 3 presentation. Connection, lesson selection, and active lesson are
mutually exclusive contexts. The selection screen keeps only the selected lesson and start action
directly visible; its list and settings icons open native bottom sheets for the catalog,
GB/US accent, and spaced review. The active lesson prioritizes the full-screen video, progress,
subtitles, transcript, error/retry, and a large hold-to-talk button. Replay, 0.75×/1×/1.25× speed,
pronunciation, and disconnect remain available through accessible icon dropdowns, sheets, and the
overflow menu. The WebRTC `SurfaceViewRenderer` remains mounted behind every context so track
attachment survives navigation. ADR-0017 records the decision.

Implementation and verification:

- `GovorTheme.kt` defines the Material 3 color/typography system. `GovorUiState.kt` owns the pure
  screen/control-visibility policy, and four new JVM tests cover connection isolation, selection
  versus active controls, teacher-playback action visibility, and retry/PTT states.
- `./scripts/test.ps1 -Scope kotlin`: verified passing; 26 JVM tests (22 existing plus four new)
  passed. The combined core/app gate now runs without the configuration cache, daemon, or parallel
  execution because the managed workspace's repository-local Gradle cache intermittently denied
  access while moving generated Kotlin DSL workspaces and reading a Gradle JAR.
- `./scripts/build.ps1 -Target android`: verified passing; API 34 compilation and debug APK
  assembly succeeded. The final debug APK is 65,554,653 bytes with SHA-256
  `9a74e4946c4d339800b8727cb0a125aa0608d9fa736251a3767d053b281f4d5e`.
  `./scripts/check-powershell-syntax.ps1 -Paths
  scripts/emulator-renderer-smoke.ps1,scripts/emulator-speech-smoke.ps1,scripts/test.ps1` also
  passed.
- `./scripts/test.ps1 -Scope all`: verified passing from the beginning; 258 Python tests at 85.11%
  branch coverage, 26 Kotlin tests, 9 C# tests, 21 real media tests, Godot import/C# build/headless
  self-test, and Android debug assembly all passed. Godot emitted only the documented Windows root-
  certificate-store message and an offline NuGet advisory-index warning.
- The first live `pip-audit` run exposed three newly published advisories against transitive
  `filelock 4.0.12`, all fixed after 4.2.1. `uv lock --upgrade-package filelock` updated only that
  package to 4.2.4; the frozen media/speech audit then reported no known vulnerabilities.
- Final `uv run --frozen pre-commit run --all-files`: verified passing after its pinned hook
  environment was allowed to download; JSON/YAML, EOF/line-ending/whitespace, private-key and
  large-file checks, Ruff check/format, contracts, PowerShell syntax, and the affected-application
  test gate all passed with the refreshed lock.
- `./scripts/emulator-renderer-smoke.ps1`: verified passing on the Android Studio API 34 AVD with
  local audio disabled. It opened the icon lesson catalog, selected the host-provided café lesson,
  opened the preferences sheet, selected American English and spaced review, proved speed was
  absent before lesson start, completed fake teacher/learner turns, exercised PTT/transcript,
  disconnected through the active overflow menu, and reconnected. Godot video reached Android as
  1280×720 frames with zero reported renderer drops in the final short interval; microphone return
  passed before and after reconnect. This is a functional smoke, not a performance benchmark.
- `./scripts/emulator-speech-smoke.ps1`: verified passing with host/emulator output muted. The speed
  icon/dropdown selected 0.75×, replay retained synchronized highlights, the pronunciation icon
  opened the word sheet, and isolated-word Kokoro playback completed. The Android log recorded the
  playback-rate change, seven highlight indices on replay, selection of word zero, and bounded
  isolated-word completion.
- Initial emulator-smoke attempts failed before producing UI evidence because the harness omitted
  the gateway-security source path, UI Automator raced emulator/sheet startup, hardware-keyboard
  mode made an obsolete Back press exit the Activity, the old PTT text selector no longer matched,
  and Windows PowerShell 5.1 misread a non-ASCII script literal. The harness now includes the
  dependency, retries hierarchy capture, avoids the keyboard Back action, selects PTT by content
  description, and uses an encoding-independent café-title match. Both complete smokes then passed.
- The smoke scripts force-stopped the app, removed `adb reverse` mappings, and stopped their host,
  media, and renderer processes. Ports 8765/8766 were not listening and Android reported
  `mMusicActiveMs=0` afterward; no tone or media server was left active.

Limits:

- The AVD is development evidence for navigation, accessibility structure, media integration, and
  reconnect only. No new physical-phone, Wi-Fi, acoustic, hardware-codec, target-performance, or
  release-package claim is inferred, and the historical Milestone 9 acceptance package predates
  this UI change.
- ADB screenshots still render the WebRTC `SurfaceView` black even when libwebrtc reports real
  1280×720 frames. The screenshot supports only the Compose overlay appearance; video evidence
  remains transport/render logs as already documented.

### Android transient lesson-state correction

On 2026-11-02 two user-observed UI defects were traced to values that outlived their valid lesson
state. `LessonSessionClient` retained a recoverable error after a successful retry and omitted the
learner transcript from its lesson-end cleanup. The app now owns both values in a small transient
presentation-state holder. It clears the final learner answer on lesson completion and before a
new lesson starts. A real recoverable/fatal error remains visible, but a subsequent normal host
state clears the recovered error card. Disconnect and lesson boundaries also remove obsolete
transient values. No wire contract, host state machine, progress record, or persisted learner data
changed.

Verification:

- `./scripts/test.ps1 -Scope kotlin`: verified passing; 31 JVM tests, zero failures/skips. Two new
  tests reproduce the final-answer lesson-boundary leak and the stale post-retry error, then verify
  the corrected lifecycle.
- The managed account again denied the Kotlin daemon marker under `%LOCALAPPDATA%`; Gradle's
  supported in-process fallback compiled production and test Kotlin and the build completed.
- `./scripts/build.ps1 -Target android`: verified passing. The debug APK is 66,058,580 bytes with
  SHA-256 `0b0f1a5a698d9f0b7b6291f8df963423996c3606732c968e7e62062fde9f011a`.
- `./scripts/package.ps1 -Version 0.1.19 -VersionCode 20 -NoArchive`: verified passing. Godot
  export, Android release lint/build, APK Signature Scheme v2 verification with the established
  signer, embedded runtime/source/import checks, prerequisites, and packaged wrapper doctors all
  completed. The signed APK is 59,891,893 bytes with SHA-256
  `30e2dc991b04d85abdebfccd01b51515ff9b853f8380f7c12807b5093d4c57ca`.
- The matching `.cache/dist/govor.ai-0.1.19-windows-x64` host passed both learner-facing doctors;
  Qwen3, Whisper, Kokoro model/voices, and Piper model/config all reported `ready`. The prior
  versioned host remains available as a rollback copy.
- The authorized physical realme updated in place from 0.1.18/code 19 to 0.1.19/code 20 with
  `adb install -r --no-streaming`, preserving application data. Android returned `Success`, the
  package query reported the new version, and `ai.govor.app/.MainActivity` completed a cold launch
  with `Status: ok` in 666 ms.
- No lesson or recovery interaction was automated after installation, so the two visible fixes
  still require direct user retesting. No host gateway/audio was started; TCP 8765/8766 remained
  closed. Exact deployment evidence is in
  `docs/benchmarks/2026-11-02-release-0.1.19-ui-fix-deployment.md`.

## Post-milestone QR-first release pairing

The 2026-10-25 maintenance feature makes a single locally scanned QR the default first pairing
path. The Windows launcher creates a strict version 1 bootstrap containing the selected LAN
endpoints, one-time code, certificate SHA-256, and expiry; Segno writes a temporary PNG below the
per-user security directory. Godot starts in an opaque, dedicated 2D connection state outside the
streamed 1280x720 viewport and dismisses it after session start. Android validates the QR locally
with ZXing and enters the
unchanged certificate-pinned HTTPS/WSS credential lifecycle. The release manual form is collapsed
under **Pair manually**; debug retains expanded controls, and stored credentials expose one-tap
reconnect. ADR-0018 records the decision.

Implementation and verification:

- Added the closed `pairing-bootstrap.schema.json`, positive/negative fixtures, launcher encoder
  tests, strict Kotlin payload/parser tests, and an exact Segno-module fixture decoded by ZXing.
  The focused Python/contract run passed 55 tests; the Android gate passed 29 JVM tests.
- The 2026-10-25 host follow-up replaces the small QR-over-scene overlay with a fully opaque 2D
  screen containing same-network guidance, three connection steps, QR expiry/status, and a
  user-opened manual dialog. The dialog exposes selectable hosts, one-time code, certificate
  fingerprint, and an explicit copy action. `session_started` transitions to the existing 3D
  lesson. No pairing secret enters process arguments or the WebRTC viewport: the launcher writes
  a second bounded protected bootstrap file, passes only both paths, and deletes both at shutdown.
- The Godot project and Windows export now use the project-owned mint speech-bubble/waveform icon.
  The source PNG, seven-size ICO derivative, generation prompt, and provenance are recorded under
  `apps/renderer/Assets/Brand`.
- `./scripts/test.ps1 -Scope all` passed: Ruff/format/mypy, 268 Python tests at 85.18% branch
  coverage, 29 Kotlin tests, 9 C# tests, 21 real media tests, Godot import/C# build/headless
  self-test, and Android debug assembly.
- `./scripts/build.ps1 -Target renderer` passed. A generated QR was loaded by the exported player
  in a bounded `--mute-local-audio --exit-after-tone` run; it exited 0 after the existing two-
  second fixture, logged no overlay/runtime error, and left no player/audio running.
- The follow-up renderer export passed, and two bounded hidden-window runs captured the real
  1280x720 default and manual states with no tone. The default proof is 123,603 bytes/SHA-256
  `4822676f425151618cdcac04826b9f1bb7a8735460cea617d753d3c2bbb65b82`; the manual proof is
  108,483 bytes/SHA-256
  `94556fdead999baf829ae248709f0b596aa1ec5d309169ca48ec0af93e607577`.
- The final signed `0.1.15`/code-16 package build passed Godot export, Android release lint/build,
  v2 signature verification with the established signer, embedded Segno installation,
  source/notices, import checks, prerequisites, and packaged wrapper doctors. Its APK is
  59,891,893 bytes with SHA-256
  `a01f9dea01bba8600ced9f5a9085c3991823e22cc9de34a8c0c370b441e52d63`.
- The follow-up signed `0.1.16`/code-17 package passed Godot export, Android release lint/build, v2
  signature verification, source/import/prerequisite checks, and packaged the branded renderer.
  Its APK is 59,891,893 bytes with SHA-256
  `c0639ae3d5c4ba02f217616e41c0eb600ffe90aae262c9aacb8477e2f325edf3`.
- The current `./scripts/test.ps1 -Scope all` passed Ruff/format/mypy, 268 Python tests at 85.18%
  branch coverage, Android/JVM tests, 9 C# tests, 21 media tests, Godot build/self-test, and Android
  debug assembly. The locked dependency audit again reported no known vulnerabilities.
- The current all-files pre-commit gate passed JSON/YAML, EOF/line-ending/whitespace, private-key
  and large-file checks, Ruff check/format, contracts, PowerShell syntax, and affected-application
  tests.
- On the audio-disabled API 34 emulator, that signed release showed **Scan host QR** as the primary
  action and no manual fields before expansion. Selecting it raised Android's in-context camera
  permission and opened the ZXing capture Activity with the expected prompt and no fatal error.
  Expanding **Pair manually** exposed the prior host/code/fingerprint diagnostics.
- The locked Python dependency audit reported no known vulnerabilities. Segno 1.6.6, ZXing
  Android Embedded 4.3.0, and transitive ZXing Core 3.4.1 are pinned and documented.
- The final all-files pre-commit gate passed JSON/YAML, EOF/line-ending/whitespace, private-key and
  large-file checks, Ruff check/format, contracts, PowerShell syntax, and affected-application
  tests.

Evidence boundary and next work:

- `adb devices -l` showed no physical device when the final candidate was ready. A real camera
  focus/scan is therefore **not executed** and is not inferred from the emulator. The exact QR
  symbol's cross-library decoding is verified in a JVM test, but that is not physical-camera
  evidence and does not alter the completed Milestone 9 record.
- Mixed PC Ethernet/phone Wi-Fi requires no media or wire-contract redesign on one routable trusted
  private LAN. At this QR checkpoint the launcher still advertised one sorted hostname-resolved
  address; the subsequent LAN-topology maintenance section records the implemented active-adapter
  selection and its still-pending physical mixed-path check.
- Exact commands and limitations are in
  `docs/benchmarks/2026-10-25-qr-first-release-pairing.md` and
  `docs/benchmarks/2026-10-25-host-preconnect-ui-and-icon.md`.

## Post-milestone mixed Ethernet/Wi-Fi LAN support

The 2026-10-25 maintenance implementation supports a Windows host on Ethernet and an Android phone
on Wi-Fi when both links are bridged or routed on the same trusted private LAN. The gateway and
WebRTC contracts were already topology-neutral; the launcher address advertisement was the missing
boundary. It now queries Windows NetTCPIP adapter/profile/route data before creating pairing state,
admits only active physical non-virtual RFC1918 addresses with a recognized Windows profile,
prefers Private, and follows the lowest active default-route plus interface metric within the
preferred category. A forwarded `Start-Govor.cmd --lan-address <IPv4>` option selects another
eligible local adapter without bypassing the same checks. ADR-0019 records the decision.

On 2026-10-26 the product owner clarified that the target Ethernet link is intentionally labeled
Public by Windows but remains an RFC1918 link behind the same trusted router that supplies phone
Wi-Fi. The original profile gate incorrectly treated a firewall/discovery category as address-
scope evidence. The selector now permits that Public-category local link, emits an explicit
trusted-router/firewall/no-port-forwarding warning, and continues to reject unidentified,
virtual/VPN, disconnected, link-local, and non-RFC1918 addresses. Private remains preferred when
both categories are eligible.

Verification and current limitation:

- The original focused run passed 32 tests. The corrected focused run passes 34 tests covering
  inventory parsing and command execution, unsafe/disconnected/virtual/unidentified filtering,
  Private-over-Public preference, deterministic route metrics, bounded explicit Public/local
  selection, QR behavior, and launcher argument forwarding.
- Corrected `./scripts/test.ps1 -Scope python` passed Ruff, formatting, strict mypy, and 285 tests
  at 85.20% branch coverage.
- `./scripts/test.ps1 -Scope python` passed from the beginning after one mypy correction: 283 tests
  at 85.23% branch coverage with strict mypy and Ruff/format checks. The initial run found only an
  `Any` return in the new integer parser; converting the already type-checked value resolved it.
- `./scripts/test.ps1 -Scope all` passed after the documentation update: the same Python gate, 29
  Kotlin tests, 9 C# tests, 21 real media tests, Godot import/build/headless self-test, and Android
  debug assembly all completed. Godot/NuGet emitted only the existing certificate/advisory-index
  environment warnings.
- The corrected final `./scripts/test.ps1 -Scope all` rerun passed with 285 Python tests at 85.20%
  branch coverage, 29 Kotlin tests, 9 C# tests, 21 real media tests, Godot import/build/headless
  self-test, and Android debug assembly. The only Python warnings were the existing Starlette
  deprecation and an environment-specific unreadable pytest cache; NuGet again could not reach its
  advisory index but the build and tests passed.
- The frozen media/speech dependency audit reported no known vulnerabilities after the expected
  sandbox network denial was repeated with approved metadata access. The corrected final audit
  also reported no known vulnerabilities.
- The all-files pre-commit gate passed JSON/YAML, line-ending/whitespace, private-key/large-file,
  Ruff check/format, contract, PowerShell syntax, and affected-application tests after its pinned
  hook environments were initialized with approved network access. A repeat after the last
  documentation edit found an unreadable cached hook manifest; a fresh workspace-local hook cache
  completed the final all-files pass. The corrected Public-profile implementation repeated the
  same complete all-files gate in a newly initialized workspace-local hook cache and passed.
- A corrected real adapter query selects active physical `Ethernet 3` at `192.168.100.72`, reports
  its Windows **Public** category, and marks the warning path active. Disconnected physical Wi-Fi
  and virtual/link-local adapters remain rejected.
- Signed portable candidate `0.1.17`/code 18 passed Godot export, Android release lint/build, APK
  Signature Scheme v2 verification, embedded-runtime import, corresponding-source, and package
  prerequisite checks. Its packaged launcher independently selected
  `192.168.100.72 Ethernet 3 Public` with `uses_public_profile=True`. The signed APK is 59,891,893
  bytes with SHA-256 `cd7ac297a79871b5c75564168265b0b0e574a6ad12494968335ec659b77bb478`.
  An initial Godot export process failed to exit and was interrupted after its output completed; a
  later Android attempt hit a stale locked Gradle transform JAR. Stopping the project Gradle daemon
  released that lock, and the complete offline package command then passed without deleting cache
  or source data.
- `adb devices -l` started the local ADB daemon but found no physical phone or emulator. An end-to-
  end check of TCP 8765/8766, authenticated WSS, ICE video/audio, and microphone return over
  Ethernet-to-access-point is therefore **blocked/not executed** on device availability, not the
  Windows profile. No passing mixed-topology claim is inferred from unit tests or the earlier all-
  Wi-Fi Milestone 9 record.
- Read-only Windows Firewall inspection found both Public and Private profiles enabled. Historical
  version-specific Python rules exist, including Public/Any rules for 0.1.0/0.1.1 and Private/Any
  rules for later old candidates, but no future corrected package path can inherit those rules.
  No firewall rule was added, removed, or changed; the exact next candidate may trigger the normal
  Windows prompt and must be allowed only for this trusted router profile.

Exact evidence, commands, and the required follow-up are in
`docs/benchmarks/2026-10-25-mixed-ethernet-wifi-lan.md`. Router guest/client isolation, unrouted
VLANs, profile-matched local-network Windows Firewall access, and no router port forwarding remain
explicit deployment requirements.

## Post-milestone guided-answer flexibility

The airport destination exercise no longer treats the beginner example's `London` as the only
valid destination. The deterministic domain matcher now supports one bounded named value slot
after a required literal phrase. `I am flying to New York`, `My flight to Sofia leaves tonight`,
and `My destination is Rio de Janeiro` advance; incomplete or directionally wrong answers do not.
The lesson-creator prompt uses the same representation for future learner-chosen values without
allowing the dialogue model to award progress.

Verification on 2026-11-02: the focused domain and lesson-creator run passed 27 tests. The only
warning was an existing environment-specific pytest temporary-directory cleanup permission issue.
The Python scope then passed Ruff, formatting, strict mypy, and 298 tests at 85.15% branch
coverage; its only warning was the existing Starlette TestClient deprecation. The full suite and
packaged runtime check remain to be rerun after the related progress, teacher-selection,
host-management, and Bulgarian-speech fixes are integrated.

## Renderer evidence and limitations

The current local proof images visibly contain the selectable facial teachers over four distinct
photographic backdrops. That post-milestone scene tour is development-machine evidence. The live
bridge and emulator evidence below predates the new visual assets: the aiortc peer logged non-black
input, Android
libwebrtc logged `Reporting first rendered frame` and a 1280x720 resolution change, application
PCM reached the first peer, and microphone frames returned to Windows before and after reconnect.
After the two-second tone ended, the second peer correctly received silence rather than a retained
PCM block. The final emulator render interval reported 120 frames in 4.002 seconds (30.0 fps), with
zero dropped frames; this short loopback sample is development evidence, not a hardware benchmark.

The ADB screenshot still shows a black video region. Because the local proof image is non-black,
the peer received non-black pixels, and Android emitted render callbacks, this is consistent with
an ADB/`SurfaceView` capture limitation, but that explanation has not been independently proven.
No screenshot-based scene-visibility claim is made.

The 2026-10-21 physical run now supplies controlled cadence, RTT/loss, CPU/GPU/RAM/VRAM,
thermals, Wi-Fi, hardware Android decode, explicit Windows software-encode fallback,
monitor-off/unfocused, lifecycle, physical microphone, and historical 1,800-second transport
evidence. The exact 0.1.11 follow-ups add café completion/restart, pronunciation, and an explicit
Bulgarian-help/English-return lesson path. Whisper did not preserve the Bulgarian phrase in the
displayed transcript, so that run is not a human-speech accuracy claim. Subjective phone
video/audio quality was confirmed by the learner on 2026-10-22. The older emulator's virtual
`c2.goldfish.vp8.decoder` remains emulator-only evidence and is not used for the physical codec
row.

Initial migration evidence is in `docs/benchmarks/2026-10-09-godot-renderer-migration.md`; original
Milestone 6 avatar/scene evidence is in
`docs/benchmarks/2026-10-12-avatar-scenes-and-renderer-performance.md`; current selectable-teacher
evidence is in `docs/benchmarks/2026-10-26-selectable-teachers-and-backdrops.md`; target evidence
for the earlier signed candidate is in
`docs/benchmarks/2026-10-21-m9-physical-release-acceptance.md`.

## Environment and artifacts

- Windows process build 10.0.26200.
- NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94.
- Godot 4.7.2 stable .NET (`ed1daf0bf`), repository-local editor and export templates.
- Physical target: realme RMX3939, Android 16/API 36, security patch 2026-08-01; intended
  `A1_B436` WPA2-Personal Wi-Fi. Its ADB serial is intentionally omitted.
- Android Studio API 34 AVD `Pixel_3a_API_34_extension_level_7_x86_64`, serial
  `emulator-5554`, used only for development evidence.
- Clean-software fixture: QEMU 11.0.50/WHPX, guest `GOVOR-M8-VM`, Windows
  10.0.22000.0 AMD64; exact-image and VM limits are recorded above.
- Renderer: `apps/renderer/Builds/Windows/GovorRenderer.exe` (ignored build output).
- Debug APK: `apps/android/app/build/outputs/apk/debug/app-debug.apk`.
- Post-audit signed APK: `.cache/dist/govor.ai-0.1.11-android-release.apk`, 55,425,173 bytes,
  SHA-256 `94662d516bfff260b3276522142bb7ce34a995f03400011df914940c10b87e2a`.
- Physical reports: ignored `.cache/m9-final-candidate-smoke.json`,
  `.cache/m9-physical-soak.json`, and `.cache/m9-011-physical-smoke.json`; committed summary in
  the dated M9 benchmark.
- Runtime logs/proof images: ignored files under `.cache/`.
- Inventory: `docs/benchmarks/local/latest-inventory.json` (inventory only, no performance claim).

## Next steps

Milestone 9 and the master-spec milestone sequence are complete. This handoff is the focused M9
closeout. Preserve the exact release/evidence artifacts and begin no additional milestone unless
the product owner defines one. Phone settings are restored and no service or audio remains active.

The evidence boundaries remain explicit: Milestone 1 used emulator development evidence, while
Milestone 9 passed only from the documented physical target execution and learner confirmation.

## Future regression commands

```powershell
git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' status --short --branch
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi -NoDownload
./scripts/test.ps1 -Scope all
$env:UV_CACHE_DIR = Join-Path (Resolve-Path '.cache').Path 'uv-m9-final'
uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m9-final
$env:PRE_COMMIT_HOME = Join-Path (Resolve-Path '.cache').Path 'pre-commit-m9-final'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = 'C:/Users/PC/Documents/GitHub/govor.ai'
uv run --frozen pre-commit run --all-files
git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' status --short --branch
```
