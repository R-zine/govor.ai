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

`packages/scene_planner` maps the four committed lesson scenario IDs to deterministic scene
specifications. The shared renderer contract permits only closed environment, camera, lighting,
transition, and asset identifiers plus bounded transforms. Godot assembles those specifications
entirely in memory from a procedural catalog, reuses cached mesh/material resources, and releases
the prior scene tree. Unknown wire asset IDs are rejected; an internal missing catalog
implementation produces a predictable magenta fallback.

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

## Teaching and progress boundary

`packages/domain` contains four committed guided lesson definitions and the deterministic
`TeachingEngine`. The active local dialogue model may classify or phrase a conversational turn,
but it cannot award progress. Only recognized English production that satisfies the active guided
exercise can advance. Bulgarian/mixed assistance, vocabulary questions, repetition, slower-speech
requests, ambiguity, and recognition failure retain the exercise.

Two failed English attempts lower difficulty by one level; two consecutive first-attempt successes
raise it by one. A closed reason enum accompanies each change. The Android client selects the
café, supermarket, airport, or home scenario and displays the host-owned progress snapshot.

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
memory mappings. aiortc is the sole network peer. The handoff adds no LAN listener and no native
plugin. Sequence locks, bounded audio storage, and writer-generation IDs reject torn data, cap
backlog, and recover from renderer restart. Godot project/build validation, local runtime, and
native-emulator delivery passed, so this architecture is accepted for Milestones 2-8. Final
physical-device, Wi-Fi, codec, performance, lifecycle, and soak acceptance remains the mandatory
Milestone 9 release gate. See ADR-0002, ADR-0003, and ADR-0004.
