# Architecture overview

govor.ai uses a native Android presentation client and a Windows host. The host owns teaching,
local AI, progress, rendering, and media production. Android owns display, playout, push-to-talk,
simple controls, and session connectivity; it performs no AI inference or 3D rendering.

## Boundaries

| Boundary | Responsibility | Must not contain |
| --- | --- | --- |
| `packages/domain` | Framework-independent session and teaching rules | FastAPI, Android, Godot, provider SDKs |
| `packages/contracts` | Versioned schemas and language bindings | Business decisions or provider behavior |
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
- `local`: future production adapters for llama.cpp, whisper.cpp, Kokoro, Bulgarian speech, and
  alignment. These are not implemented in Milestone 0.
- `cloud`: optional future adapters, independently configured, opt-in, and disabled by default.

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
