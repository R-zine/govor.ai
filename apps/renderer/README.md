# Windows renderer

`apps/renderer` is the active Godot 4.7.2 .NET renderer. Unity is not part of the stack.

The runtime owns a 1280x720, 30 fps `SubViewport`, a repository-owned CC0 stylized teacher, and
four deterministic procedural environments: café, supermarket, airport, and home. The avatar has
idle, speaking, listening, and thinking behavior, simple expressions, PCM-energy mouth motion, and
six viseme shapes. Scene specifications and animation timelines arrive through the validated
loopback renderer-control contract; no command can name a path, URL, download, or script.

The scene catalog caches reusable primitive meshes/materials and assembles each environment
entirely in memory. Replaced scene trees are queued for cleanup. Unknown wire assets are rejected;
an internal missing implementation has a deterministic magenta fallback. See
`Assets/Teacher/README.md` and ADR-0009 for the asset/license and boundary decisions.

Godot publishes top-to-bottom RGBA frames and bounded PCM blocks through renderer-neutral Windows
named memory mappings. Video uses two alternating latest-frame slots so a complete frame remains
readable while the next slot is filled; audio uses a bounded 64-block ring of 20 ms blocks. The
mappings open no network listener, while aiortc remains the only network-facing media
implementation.

`RendererSessionController` connects outward to the host's loopback-only
`/v1/renderer/control` WebSocket. It validates the shared C# contract, applies only closed session,
scene, and avatar data, and acknowledges each command. The host derives mouth energy from the
actual speech WAV and sends visemes only when the provider supplied phoneme timing.

Install the pinned editor/export templates, validate, export, and run the bounded checks:

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer
./scripts/test.ps1 -Scope godot
./scripts/build.ps1 -Target renderer
./scripts/renderer-smoke.ps1
./scripts/renderer-scene-smoke.ps1
./scripts/benchmark.ps1 -Profile renderer
./scripts/emulator-renderer-smoke.ps1
./scripts/emulator-speech-smoke.ps1
```

`renderer-smoke.ps1` verifies changing non-black frames and the bounded application-owned PCM
tone; it is muted by default. Pass `-Audible` only for a supervised two-second PC speaker check.
The scene smoke captures all four environments, requires four distinct hashes, checks cache/video-
memory stability on revisit, measures frame/build/transition/avatar/software-encoding costs, and
exits without leaving audio or a player running. The renderer benchmark repeats the scene tour
while Qwen3 4B handles real requests and proves their measurement windows overlap.

Pass `--control-url=ws://127.0.0.1:8765/v1/renderer/control` after Godot's `--` separator for
ordinary development and `--no-startup-tone --mute-local-audio` when the bounded media tone is not
needed. `--scene-tour-output=<directory>` is a trusted local benchmark option, not a wire field.

The release launcher instead passes
`--control-url=wss://localhost:8765/v1/renderer/control` plus
`--control-ca=<protected per-user certificate>`. The renderer still connects outward to loopback;
the CA option does not expose a renderer listener or make certificate verification optional.

Godot import/build/self-test and emulator results remain development evidence only. The dated
Milestone 9 ledger records physical Wi-Fi transport, hardware decode, cadence/resources,
lifecycle recovery, monitor-off operation, and bounded stability on the target machine. The
historical 30-minute transport run exceeds the current requirement; there is no fixed-duration
lesson or soak release gate.
