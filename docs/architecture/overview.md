# Architecture overview

govor.ai uses a native Android presentation client and a Windows host. The host owns teaching,
local AI, progress, rendering, and media production. Android owns display, playout, push-to-talk,
simple controls, and session connectivity; it performs no AI inference or 3D rendering.

## Boundaries

| Boundary | Responsibility | Must not contain |
| --- | --- | --- |
| `packages/domain` | Framework-independent session and teaching rules | FastAPI, Android, Godot, provider SDKs |
| `packages/contracts` | Versioned schemas and language bindings | Business decisions or provider behavior |
| `packages/scene_planner` | Deterministic validated scene and avatar-animation plans | Godot nodes, paths, downloads, lesson policy |
| `apps/host` | Windows orchestration and authenticated gateway | Model-specific logic in route handlers |
| `services/*` | Replaceable provider and media adapters | Lesson policy |
| `apps/renderer` | Render scenes and expose frames/audio | Dialogue or progress logic |
| `apps/android` | Native Material 3 stream, audio, PTT, subtitles, and contextual controls | AI inference or 3D scene generation |

Dependencies point inward toward domain rules and provider interfaces. Cross-process messages use
JSON contracts with protocol version, message type, UUID correlation identifier, and validated
payload. Audio/caption/animation timelines use integer microseconds relative to the start of a
media item. Wall-clock timestamps are UTC ISO 8601 and are never used for media synchronization.

## Provider modes

- `fake`: deterministic scripted lesson and generated test tone. Development/test only, labeled
  in health and response metadata.
- `local`: real loopback-only llama.cpp dialogue, whisper.cpp multilingual recognition, Kokoro
  English speech, Piper Bulgarian speech, and eSpeak NG fallback. The selected dialogue model is
  Qwen3 4B Q4_K_M; deterministic policy owns teaching invariants and bounded session memory.
  Provider-reported alignment is optional and never estimated.
- `cloud`: OpenAI-compatible dialogue, transcription, and WAV speech adapters. Each subsystem is
  selected independently. Cloud use requires disabling the offline-only gate; microphone upload
  requires a second explicit consent. Credentials are current-user Windows credentials and are
  resolved only when a request is made.

The host should remain useful in deterministic scripted lesson mode if local model inference
fails. That fallback is a real product behavior distinct from development fakes.

## Session control

Milestone 2 establishes the host as the only orchestration authority. Android connects to
`/v1/control`, sends validated lifecycle events, and renders host-owned session state. Godot
connects outward to the host's loopback-only `/v1/renderer/control` endpoint; it accepts only six
allow-listed visual actions and acknowledges each command. The renderer never receives dialogue
policy or arbitrary code, paths, or URLs.

Provider calls run in cancellable tasks with explicit deadlines, while playback and recording
steps have their own deadlines. A connection owns at most one lesson session, and disconnect/end
cancels outstanding work, resets the renderer, and removes the session from the host registry.
See ADR-0005.

## Android presentation boundary

Android derives exactly one connection, lesson-selection, or active-lesson context from the media
and host session state. Connection fields do not share a screen with lesson controls. Selection
keeps the primary start action visible and places catalog/preferences in Material 3 sheets; the
active context places replay, speed, pronunciation, and disconnect in icon menus while subtitles,
progress, errors/retry, and push-to-talk remain direct. Stable accessibility descriptions are part
of this presentation contract. The mapping and control visibility are pure Kotlin policy with JVM
tests. See ADR-0017.

The Compose overlay changes by context, but its native `SurfaceViewRenderer` stays mounted for the
Activity lifetime. This lets an existing or newly arriving WebRTC track retain its sink through UI
transitions and reconnects.

## Speech boundary

`services/speech` owns local synthesis and phonemization adapters. English `en-GB` and `en-US`
route to distinct Kokoro voices; `bg-BG` routes to Piper; provider failure routes to process-isolated
eSpeak NG. The host emits bounded PCM16 WAV, exact pronunciation character ranges, and nullable
model-derived word/phoneme alignment. Android owns `AudioTrack` playout, media-time highlighting,
0.75×/1×/1.25× speed, full replay, word selection, IPA/explanation display, and isolated-word
playback. Godot and the domain do not depend on a speech SDK. See ADR-0007.

Local bilingual replies are split at Latin/Cyrillic script changes before synthesis. Kokoro uses
the learner's English accent; Piper handles Bulgarian spans. Actual PCM is resampled to 24 kHz
and concatenated. Pronunciation character offsets, word indices, and real timestamps are shifted
to the combined timeline; if any span lacks an alignment type, that combined type is null.
Fallback is applied per span so a provider failure cannot force both languages into one voice.

Phone lesson creation is owned by `LessonCreationJobs`, separately from cancellable lesson work.
It survives phone socket teardown and keeps one bounded latest status per authenticated device.
The phone explicitly re-queries status on reconnect, while a closed loopback display message
updates the host pre-lesson progress UI. ADR-0014 defines timeout, ownership, and restart limits.

While the WebRTC lesson session is connected, Android selects the built-in loudspeaker as the
communication device and reasserts that selection when the remote audio track starts. Android 12+
uses the communication-device API; Android 8-11 uses the speakerphone compatibility API. The
pre-session route and audio mode are restored on disconnect, background teardown, or failure.

## Scene and avatar boundary

`packages/scene_planner` combines four built-in templates with strictly validated local recipes
from `assets/environment-content` in development or `content/environments` in a release. A lesson
selects one current planner ID independently of its scenario ID. The built-in IDs resolve inside
Godot to reviewed, packaged CC0 photographic backdrops. Imported objects use only closed
box/cylinder/sphere primitives, hex colors, and bounded dimensions/transforms. Godot assembles the
selected backdrop or primitive scene in memory, reuses cached resources, and releases the prior
scene tree. Unknown built-in asset IDs are rejected; an internal missing primitive implementation
produces a predictable magenta fallback. Imported data cannot name a path, URL, Godot resource,
script, model, texture, or assembly. See ADR-0009, ADR-0015, and ADR-0020.

The active teacher is one of three packaged CC0 skinned models: Elena, Amira, or Daniel. Each has
34 facial blend shapes, including 14 speech visemes. The host pre-connect screen persists a closed
profile ID; the renderer applies that model and the speech router resolves female/male voices from
the same state. The host derives a bounded energy envelope from actual synthesized PCM. Real
provider phoneme timing is converted to visemes; when timing is unavailable the viseme list stays
empty and only PCM energy drives a generic mouth opening. The model cannot select scenes, teacher
profiles, or avatar actions. See ADR-0009 and ADR-0020.

## Local AI boundary

`packages/provider_interfaces` defines framework-neutral recognition, dialogue, speech, and lesson
types. `services/local_ai` adapts the pinned local runtimes; it does not own session transport.
`services/provider_router` composes independent local/cloud choices and owns the outbound cloud
gate plus Windows credential boundary. Generic structured dialogue encoding is shared at the
provider-interface boundary so local and compatible cloud output receives identical validation.
`packages/domain` owns conservative script-level language detection, explicit help-intent
classification, the bilingual policy, lesson context, and a configurable bounded history window.

The llama.cpp server accepts OpenAI-compatible requests only on loopback. Model output is
constrained to a closed JSON schema, parsed with unknown fields forbidden, then passed through the
deterministic policy. The policy prevents clarification, reformulation, repeat, slower-speech,
vocabulary, ambiguity, and recognition-error turns from advancing an exercise. whisper.cpp reads
one temporary WAV and produces one bounded JSON file; both are deleted after the call. A successful
empty recognition is distinct from malformed provider output and produces a repeat request without
an invented transcript. The server URL, provider identity, model path, context size, GPU layers,
and memory window are configurable without changing domain code. See ADR-0006.

The Windows and paired-phone lesson creator use that loopback llama.cpp process through the closed
`local-ai-lesson-content` shape. The phone reaches it only through a bounded request on the
existing authenticated control connection; llama.cpp itself remains loopback-only. The model
supplies bounded teaching prose only.
Deterministic code resolves omitted creator options and owns all identifiers, ordering, the
allow-listed scene, validation, and publication. It never routes generated text into a command or
renderer asset. See ADR-0014.

## Teaching and progress boundary

`assets/lesson-content` contains the versioned JSON lesson definitions. At startup,
`packages/domain` strictly loads the complete directory into an immutable ordered catalog; the
packaged copy and additive user imports live under `content/lessons`. Invalid or duplicate content
fails startup. `Manage-Lessons.cmd` opens a native Windows picker and passes one local `.json` or
`.zip` to the launcher importer. That boundary validates all entries, the combined catalog, and
current planner scene IDs before publishing files under an import lock. The host polls the directory,
atomically swaps only a complete valid snapshot, and pushes its bounded summary over existing
authenticated control connections. Android updates its selector without reconnecting. Active
lessons retain their original catalog/service snapshot; subsequent lessons use the replacement.
Invalid out-of-band edits leave the last valid catalog active and mark health as `reload_error`.
`Create-Lesson.cmd` and the Android lesson-selector action collect a required topic plus optional
difficulty, scene, and one-to-eight exercise length. They validate structured local-model output,
assemble deterministic fields, and enter the catalog through the same locked importer. Android's
request is allowed only on the paired control WebSocket before a lesson; there is no runtime
download or separate administration endpoint. The deterministic `TeachingEngine` consumes the
selected definition.
`Manage-Environments.cmd` accepts only a bounded data-only ZIP, validates the complete combined
catalog, and publishes canonical recipes under an import lock. The host atomically swaps immutable
planner snapshots; new lessons and the lesson creator see installed display names without restart.
Invalid changes retain the previous planner and mark local health
`environment_catalog_status=reload_error`. See ADR-0015.
Godot's pre-connect **Content & updates** menu is the discoverable UI for those three exact local
entry points. It does not implement an importer or expose an administration route. Its fourth
action confirms an application update, exits with a closed launcher signal, waits for managed host
process cleanup, and only then opens the package-owned signed updater. See ADR-0021.
The active local dialogue model may classify or phrase a conversational turn,
but it cannot award progress. Only recognized English production that satisfies the active guided
exercise can advance. Bulgarian/mixed assistance, vocabulary questions, repetition, slower-speech
requests, ambiguity, and recognition failure retain the exercise.

Two failed English attempts lower difficulty by one level; two consecutive first-attempt successes
raise it by one. A closed reason enum accompanies each change. The Android client selects a lesson
advertised by the host and displays the host-owned progress snapshot.

`packages/progress` is the replaceable SQLite adapter. It persists structured settings, exercise
counters, vocabulary outcomes/review dates, completion, and difficulty history. Its schema has no
audio or transcript column. Interrupted active lessons resume; completed lessons start a new
attempt when selected again. View/export/confirmation-gated deletion is available through
`scripts/progress.ps1`. See ADR-0008.

## Media architecture decision

Milestone 1 proved the riskiest development path before full teaching work. The target was WebRTC
video and teacher audio from Windows to native Android and microphone audio in the reverse
direction. The
signaling/control protocol is ours; renderer integration remains replaceable. Godot 4.7.2 .NET is
the selected renderer and lives in `apps/renderer`. It owns a 1280x720 `SubViewport`, scene
animation, and application PCM, but does not own signaling or WebRTC.

The renderer writes RGBA readbacks and bounded PCM blocks into versioned Windows-local named
memory mappings. Video alternates between two complete latest-frame slots; the reader verifies a
stable committed header and may briefly await the next publication to avoid producer/consumer
phase aliasing. aiortc is the sole network peer. The handoff adds no LAN listener and no native
plugin. Sequence locks, bounded audio storage, and writer-generation IDs reject torn data, cap
backlog, and recover from renderer restart. Godot project/build validation, local runtime, and
native-emulator delivery passed. Milestone 9 has since measured this path on a physical phone and
target PC, completed the bounded bilingual lesson/restart path, and received learner confirmation
of moving phone video and intelligible teacher audio. Milestone 9 is complete. See ADR-0002,
ADR-0003, and ADR-0004.

## Release packaging boundary

Milestone 8 uses a versioned portable Windows x64 archive and a signed native Android APK. The
archive embeds CPython, pinned Python packages, the exported Godot player, llama.cpp, whisper.cpp,
configuration, guides, notices, and corresponding source; model weights are installed separately
from an exact size/SHA-256 manifest. Mutable models, progress, logs, TLS identity, and hashed device
credentials live below `%LOCALAPPDATA%\govor.ai` so application updates do not replace them.

The launcher is the only release process owner. It forces local/offline providers, starts
loopback inference plus authenticated HTTPS/WSS LAN gateways, creates protected short-lived
pairing artifacts, and places all children in a kill-on-close Windows Job Object. The Godot window
starts in an opaque 2D QR-first connection state with instructions, expiry status, and a manual
fallback; the underlying 3D lesson becomes visible only after `session_started`. This host UI is
outside the 1280x720 WebRTC capture viewport. The exported Windows player uses the govor.ai brand
icon rather than the Godot default.
Android pins the displayed certificate and encrypts its random device credential with Android
Keystore. ADR-0011 records the package/update/security decision. A development-machine/emulator
release lesson passes. ADR-0012 adds a QEMU/WHPX clean-Windows base/overlay fixture that routes the
host Android emulator through loopback TCP and fixture-only UDP ICE forwards. The final 0.1.4 guest
setup/start/media/shutdown run closes Milestone 8's clean-software gate for the exact recorded VM
image; it does not replace Milestone 9 hardware acceptance.

Before creating pairing artifacts, the launcher inventories Windows IPv4 adapters and advertises
only an active physical RFC1918 address with a recognized Windows network category. It prefers a
Private profile, then follows the lowest active default-route metric; a bounded `--lan-address`
override can select only another eligible local address. A Public-profile RFC1918 adapter is
allowed with an explicit trusted-router/firewall warning because that Windows label does not make
the address internet-routable. This supports a wired Windows host and Wi-Fi phone on the same LAN
without changing gateway or WebRTC contracts, while refusing VPN/virtual, disconnected,
unidentified, non-RFC1918, and link-local interfaces. See ADR-0019.

Updater-capable releases additionally pin an RSA-3072 application-update public key and include a
stable local patch bootstrap. A `.govorpatch` is data until that installed bootstrap authenticates
its signed manifest, verifies exact base/new hashes, stages the complete bounded payload, and
commits it with failure rollback and the release marker last. The bootstrap/trust key cannot update
themselves. An optional bound APK is saved for explicit Android platform installation; no update
route is exposed on the LAN. See ADR-0016.
