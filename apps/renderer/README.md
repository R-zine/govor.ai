# Windows renderer

`apps/renderer` is the active Godot 4.7.2 .NET renderer. Unity is not part of the current stack.
The previous Unity proof was removed after its license requirement blocked runtime verification.

The Milestone 1 scene contains an animated teacher placeholder, a dedicated 1280x720 `SubViewport`
at 30 frames per second, and a two-second application-owned 48 kHz mono tone. The tone stops
automatically. Pass `--mute-local-audio` after Godot's `--` argument separator when audible local
playback is not wanted.

Godot publishes RGBA frames and bounded PCM blocks through the same renderer-neutral Windows named
memory mappings already consumed by the aiortc peer. The mappings open no network listener. Video
uses a latest-frame slot; audio uses a bounded 64-block ring of 20 ms blocks. aiortc remains the
only network-facing media implementation.

For Milestone 2, `RendererSessionController` optionally connects outward to the host's
loopback-only `/v1/renderer/control` WebSocket. It validates the shared C# contract, applies only
allow-listed session/avatar actions, and acknowledges each command. Pass
`--control-url=ws://127.0.0.1:8765/v1/renderer/control` after Godot's `--` separator. Pass
`--no-startup-tone` for ordinary development; the two-second tone remains only in bounded media
smokes.

Install the pinned editor and export templates, verify the project, and export the Windows player:

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer
./scripts/test.ps1 -Scope godot
./scripts/build.ps1 -Target renderer
./scripts/renderer-smoke.ps1
./scripts/emulator-renderer-smoke.ps1
```

The smoke command is muted by default and verifies multiple changing frames, non-silent bridge PCM,
non-black RGB content, the bounded tone window, clean process exit, and an empty runtime error log.
Pass `-Audible` only for a supervised two-second PC speaker check.

Run the editor/player briefly with `--exit-after-tone` during visual checks and confirm it exits.
Then start the media peer with `-Source Renderer`; use `adb reverse tcp:8766 tcp:8766` for emulator
development. Stop both processes immediately after audio verification.

Godot import/build/self-test success does not prove GPU readback cadence, audible output, Android
delivery, hardware codecs, physical Wi-Fi, latency, or soak behavior. Record each runtime result
separately, and never report emulator evidence as physical-device acceptance. Those physical and
target-environment checks are deferred to the mandatory Milestone 9 release gate.
