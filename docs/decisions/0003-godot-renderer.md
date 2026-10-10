# ADR-0003: Select Godot .NET as the renderer

- Status: accepted for continued development; physical performance is a Milestone 9 release gate
- Date: 2026-10-09

## Context

The first renderer proof used Unity C#, but editor import, tests, player export, and runtime checks
were blocked by license activation. The renderer contained only a placeholder scene and local
media publishers; the Android client and aiortc media peer were already engine-independent.

The project needs an open renderer that supports Windows 3D authoring, animation, application PCM,
repeatable command-line export, and access to a 1280x720 render surface. It must not take ownership
of signaling, WebRTC, teaching policy, or learner data.

## Decision

Use the MIT-licensed Godot 4.7.2 .NET distribution and C# for the Windows renderer. The active
project is `apps/renderer`; no Unity project or Unity build path remains in the repository.

The renderer owns:

- scene nodes, cameras, lighting, avatar/environment animation, and visual assets;
- a dedicated 1280x720 `SubViewport` targeting 30 frames per second;
- application-owned PCM generation/playback; and
- publication to the process-local mappings defined by ADR-0002.

The renderer does not own:

- WebRTC, signaling, pairing, authentication, or LAN listeners;
- lesson/session/domain policy;
- speech recognition, language models, or provider selection; or
- persistence and learner progress.

Use the Godot .NET build because the existing bridge protocol and Windows `MemoryMappedFile`
implementation are C#. Bootstrap downloads the exact editor and export-template artifacts into
ignored repository-local directories and verifies their published SHA-512 hashes. Normal end-user
packaging will ship only the exported renderer, not the editor.

## Alternatives considered

- Stride: viable MIT/C# fallback, but its smaller volunteer-maintained ecosystem increases
  discovery and maintenance risk.
- O3DE: permissive but its C++/CMake toolchain and hardware/disk requirements are disproportionate
  to this renderer.
- MonoGame: open but framework-level; it would require substantially more custom scene, animation,
  and authoring infrastructure.
- A custom native renderer: maximum control but unnecessary before the simpler engine path is
  measured.

## Consequences and risks

- No account, activation server, seat allocation, or proprietary engine license is required.
- Godot C# source and the bridge layout can be tested and exported from scripts.
- `ViewportTexture.GetImage()` is a synchronous GPU-to-CPU readback in the initial proof and may
  fail the 720p30 resource/latency target. This must be measured, not inferred from compilation.
- If readback is too costly, preserve Godot for scene production while testing a GDExtension or
  native capture/hardware-encoding bridge. Reconsider Stride only if that smaller change fails.
- Godot import, headless self-test, Windows export, live viewport/audio, emulator delivery, and
  physical acceptance are distinct evidence rows. Passing one never implies another; ADR-0004
  places the physical rows in Milestone 9.

## Acceptance for the migration proof

1. Pinned Godot editor/templates install without an account and pass checksum validation.
2. Headless project import, C# build, self-test, and Windows export pass.
3. A brief local run shows the animated scene and stops its diagnostic tone after two seconds.
4. Godot-originated video/audio reach the native Android emulator while microphone frames still
   reach Windows and reconnect succeeds.
5. A bounded emulator frame-cadence sample and clean reconnect/teardown are recorded.

These migration-proof criteria are complete. Physical Android, Wi-Fi, hardware-codec,
latency/resource, orientation, unfocused/monitor-off, and soak evidence remains mandatory in
Milestone 9 and is not inferred from this proof.

## Evidence on 2026-10-09

- Checksum-pinned editor/template bootstrap, headless import, zero-warning C# build, renderer
  self-test, and Windows export passed.
- The exported renderer produced a visible local proof image, multiple changing non-black bridge
  frames, and non-silent PCM, then stopped its two-second tone and exited cleanly.
- The aiortc peer received non-black 1280x720 Godot pixels and 48 kHz PCM. Android libwebrtc
  reported its first rendered 1280x720 frame, and emulator microphone frames reached Windows.
- ADB screencapture showed a black WebRTC surface despite the transport and render callbacks, so
  it is explicitly inconclusive and is not treated as scene-visibility evidence.
- Disconnect/reconnect passed while the renderer stayed active: the second peer received a
  non-black frame and a second microphone return, teardown was clean, and stale retained tone PCM
  was not replayed. The bounded emulator interval reached 120 rendered frames over 4.001 seconds
  with zero drops. Controlled target-hardware measurements remain open for Milestone 9.
