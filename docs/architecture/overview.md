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
| `apps/android` | Native stream, audio, PTT, subtitles, settings | AI inference or 3D scene generation |

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

## Speech boundary

`services/speech` owns local synthesis and phonemization adapters. English `en-GB` and `en-US`
route to distinct Kokoro voices; `bg-BG` routes to Piper; provider failure routes to process-isolated
eSpeak NG. The host emits bounded PCM16 WAV, exact pronunciation character ranges, and nullable
model-derived word/phoneme alignment. Android owns `AudioTrack` playout, media-time highlighting,
0.75×/1×/1.25× speed, full replay, word selection, IPA/explanation display, and isolated-word
playback. Godot and the domain do not depend on a speech SDK. See ADR-0007.

## Scene and avatar boundary

`packages/scene_planner` maps four closed scene-template IDs to deterministic scene
specifications. A validated lesson selects one of those templates independently of its scenario
ID, so additional lesson content can reuse an environment without changing renderer code. The
shared renderer contract permits only closed environment, camera, lighting, transition, and asset
identifiers plus bounded transforms. Godot assembles those specifications entirely in memory from
a procedural catalog, reuses cached mesh/material resources, and releases the prior scene tree.
Unknown wire asset IDs are rejected; an internal missing catalog implementation produces a
predictable magenta fallback.

The active teacher is a repository-owned CC0 stylized procedural avatar. It animates idle,
speaking, listening, thinking, gestures, and basic expressions. The host derives a bounded energy
envelope from the actual synthesized PCM. Real provider phoneme timing is converted to visemes;
when that timing is unavailable the viseme list stays empty and only PCM energy drives a generic
mouth opening. The model cannot select scenes or avatar actions. See ADR-0009.

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

The separate Windows lesson creator also uses that loopback llama.cpp process, but through the
closed `local-ai-lesson-content` shape. The model supplies bounded teaching prose only.
Deterministic code resolves omitted creator options and owns all identifiers, ordering, the
allow-listed scene, validation, and publication. It never routes generated text into a command or
renderer asset. See ADR-0014.

## Teaching and progress boundary

`assets/lesson-content` contains the versioned JSON lesson definitions. At startup,
`packages/domain` strictly loads the complete directory into an immutable ordered catalog; the
packaged copy and additive user imports live under `content/lessons`. Invalid or duplicate content
fails startup. `Manage-Lessons.cmd` opens a native Windows picker and passes one local `.json` or
`.zip` to the launcher importer. That boundary validates all entries, the combined catalog, and
closed scene IDs before publishing files under an import lock. The host polls the directory,
atomically swaps only a complete valid snapshot, and pushes its bounded summary over existing
authenticated control connections. Android updates its selector without reconnecting. Active
lessons retain their original catalog/service snapshot; subsequent lessons use the replacement.
Invalid out-of-band edits leave the last valid catalog active and mark health as `reload_error`.
`Create-Lesson.cmd` collects a required topic plus optional difficulty, scene, and one-to-eight
exercise length. It validates structured local-model output, assembles the deterministic fields,
and enters the catalog through the same locked importer. There is no runtime network download or
LAN administration endpoint. The deterministic `TeachingEngine` consumes the selected definition.
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
loopback inference plus authenticated HTTPS/WSS LAN gateways, displays the PC address/certificate
fingerprint/one-time pairing code, and places all children in a kill-on-close Windows Job Object.
Android pins the displayed certificate and encrypts its random device credential with Android
Keystore. ADR-0011 records the package/update/security decision. A development-machine/emulator
release lesson passes. ADR-0012 adds a QEMU/WHPX clean-Windows base/overlay fixture that routes the
host Android emulator through loopback TCP and fixture-only UDP ICE forwards. The final 0.1.4 guest
setup/start/media/shutdown run closes Milestone 8's clean-software gate for the exact recorded VM
image; it does not replace Milestone 9 hardware acceptance.
