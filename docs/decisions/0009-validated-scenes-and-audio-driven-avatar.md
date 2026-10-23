# ADR-0009: Validated procedural scenes and audio-driven avatar

- Status: accepted
- Date: 2026-10-12
- Amended: 2026-10-23 (bounded custom procedural primitives)
- Milestone: 6

## Context

The renderer needs a visible teacher, four lesson environments, and speech animation without
letting lesson text or model output choose files, downloads, scripts, or arbitrary scene nodes.
Phoneme alignment is available for some real speech and explicitly unavailable for fallback
speech. Scene changes must also remain bounded when local inference is using most of the
development machine's memory.

## Decision

Use a repository-owned stylized teacher assembled from Godot primitive meshes. The original visual
design and scene recipe are dedicated to the public domain under CC0 1.0; no downloaded model,
texture, or binary asset is required. The avatar has idle breathing/blinking, speaking gestures,
listening and thinking poses, encouraging facial state, six closed mouth shapes, and an energy-
driven mouth opening.

Create `packages/scene_planner` as a framework-independent mapping from the four committed lesson
scenario IDs to deterministic scene specifications. Each specification contains only bounded
numbers and closed identifiers for environment, camera, lighting, transition, and catalog assets.
The shared version 1 renderer command carries the validated specification at session start. Godot
constructs the environment in memory from its closed procedural catalog; it never interprets a
path, URL, script, model-generated node type, or remote asset reference.

ADR-0015 extends the same boundary with locally installed data-only recipes. Built-in objects keep
their closed catalog IDs; custom objects contain only one closed primitive shape, bounded size,
hex color, transform, and application-owned instance ID. Environment IDs are bounded slugs
resolved from a validated planner snapshot rather than an unrestricted resource name.

Derive mouth energy from the actual mono PCM16 WAV at 40 ms intervals. Convert phonemes to the six
viseme shapes only when the selected speech provider supplied real phoneme timing. When alignment
is unavailable, send an empty viseme sequence with source `none`; the PCM envelope still drives a
generic opening and no timing is estimated. All offsets use integer microseconds from audio start.

Cache reusable mesh/material resources, replace the active scene tree atomically, and queue the
old tree for cleanup. A short fade is the only initial transition. An internal magenta fallback is
deterministic if an allow-listed catalog implementation is missing, while an untrusted unknown
asset ID is rejected by the contract before rendering.

## Security and privacy consequences

- Built-in asset IDs and custom primitive shapes are closed at the Python, JSON Schema, and C#
  boundaries; environment IDs are bounded and must exist in the validated local planner.
- LLM output cannot select an environment, asset, path, URL, script, or executable content.
- Scene and avatar payloads contain no learner transcript, credential, or microphone recording.
- PCM is summarized into bounded integer energy samples; renderer commands do not duplicate the
  audio bytes.
- The Godot control connection remains outbound and loopback-only.

## Rejected

- Directly loading a model-selected `.glb` or resource path: this would turn untrusted text into a
  filesystem/resource capability.
- Runtime asset downloads: they conflict with offline operation, reproducibility, licensing
  review, and the loopback security boundary.
- Guessing phoneme timing from text: it would violate the actual-or-null timing contract.
- A new native renderer or lip-sync dependency: the required bounded animation and scenes are
  achievable with the pinned Godot runtime and existing media boundary.
- Retaining old scene nodes indefinitely: a small shared resource cache plus queued scene-tree
  cleanup is sufficient and measurable.

## Evidence and limits

Pure tests validate all four deterministic recipes, PCM energy extraction, provider-timed visemes,
missing-alignment behavior, and arbitrary-asset rejection. The exported runtime captured four
distinct environment images, used no fallback, and showed zero cache or reported video-memory
growth on a cached revisit. Real Kokoro timing reached Godot as 23 viseme cues plus 51 PCM energy
samples. A concurrent Qwen3 4B run overlapped two inference requests with the renderer scene tour.

These are Windows development-machine and Android-emulator results. Software VP8 was measured;
physical phone, Wi-Fi, acoustics, target-machine resource behavior, monitor-off operation,
thermals, and bounded stability later passed separately in Milestone 9. Windows remained on the
explicit measured software-encoding fallback; no hardware-encoding claim is made.
