# Windows renderer

`apps/renderer` is the active Godot 4.7.2 .NET renderer. Unity is not part of the stack.

The runtime owns a 1280x720, 30 fps `SubViewport`, three bundled CC0 facially rigged 3D teachers,
and four local CC0 photographic backdrops (café, supermarket, airport, and home). The pre-connect
screen and Android lesson-preferences sheet let the user choose Elena, Amira, or Daniel before a
lesson and persist the choice. Each model has 34 facial blend shapes, including 14 speech visemes;
actual PCM energy plus provider timing drive the mouth. Validated data-only custom environments
continue to use bounded procedural primitives.
Scene specifications, animation timelines, and the closed teacher selection arrive through the
validated loopback renderer-control contract; no command can name a path, URL, download, or script.

Built-in scene IDs resolve only to the four packaged backdrop resources. The scene catalog caches
those textures plus reusable primitive meshes/materials; custom recipes contain only bounded
colored box/cylinder/sphere primitives. Replaced scene trees are queued for cleanup. Unknown wire
assets are rejected; an internal missing primitive implementation has a deterministic magenta
fallback. No custom bundle is loaded by Godot and no recipe can name a resource path or script:
the host sends the validated primitive payload over the existing control connection. See
`Assets/Backdrops/README.md`, `Assets/Teacher/README.md`, ADR-0009, ADR-0015, and ADR-0020.

Godot publishes top-to-bottom RGBA frames and bounded PCM blocks through renderer-neutral Windows
named memory mappings. Video uses two alternating latest-frame slots so a complete frame remains
readable while the next slot is filled; audio uses a bounded 64-block ring of 20 ms blocks. The
mappings open no network listener, while aiortc remains the only network-facing media
implementation.

`RendererSessionController` connects outward to the host's loopback-only
`/v1/renderer/control` WebSocket. It validates the shared C# contract, applies only closed session,
scene, avatar, and teacher-profile data, and acknowledges each command. The host derives mouth
energy from the actual speech WAV and sends visemes only when the provider supplied phoneme
timing. The host uses the same selected profile to choose a matching female or male speech voice;
accent selection remains independent. A closed selection arriving from Android is sent back over
this loopback connection, updates the model and host menu, and is persisted by the same catalog.

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
`--control-ca=<protected per-user certificate>` and
`--pairing-qr=<protected temporary PNG>` and
`--pairing-bootstrap=<protected temporary JSON>`. These paths feed an opaque host-only 2D
pre-connect screen outside the captured `SubViewport`; it shows instructions, status, expiry,
the QR, the teacher menu, a **Content & updates** menu, and a user-opened manual fallback without
putting secret values in process arguments. Content actions launch only exact package-owned local
entry points. Application patching confirms, exits with the closed launcher signal, and opens the
signed updater only after managed services stop. It is not sent to the phone as video and is
dismissed when a session starts.
The paired Android client separately exposes bounded lesson creation beside its lesson selector;
lesson/environment file import and application patching remain host-local operations.
The renderer still connects outward to loopback; none of these options exposes a renderer listener
or makes certificate verification optional.

The project and exported Windows executable use `Assets/Brand/govor-icon.png` and its
multi-resolution `.ico` derivative. `--ui-proof-image=<path> --exit-after-ui-proof` captures the
complete host UI for a bounded local visual check; add `--show-manual-pairing` to exercise the
fallback state. These are trusted local test arguments, not wire fields.

Godot import/build/self-test and emulator results remain development evidence only. The dated
Milestone 9 ledger records physical Wi-Fi transport, hardware decode, cadence/resources,
lifecycle recovery, monitor-off operation, and bounded stability on the target machine. The
historical 30-minute transport run exceeds the current requirement; there is no fixed-duration
lesson or soak release gate.
