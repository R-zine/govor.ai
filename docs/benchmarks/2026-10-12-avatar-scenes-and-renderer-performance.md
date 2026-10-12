# Milestone 6 avatar, scenes, and renderer performance — 2026-10-12

This report contains Windows development-machine and Android-emulator evidence. It is not the
Milestone 9 physical-phone, Wi-Fi, hardware-codec, acoustic, target-machine, or soak benchmark.

## Environment

- Repository: `C:\Users\PC\Documents\GitHub\govor.ai`.
- Windows process build 10.0.26200.
- Godot 4.7.2 stable .NET (`ed1daf0bf`), 1280x720 at a 30 fps target.
- NVIDIA GeForce RTX 3060, 12,288 MiB, driver 560.94.
- Qwen3 4B Q4_K_M through pinned llama.cpp b11540 Vulkan.
- Android Studio API 34 AVD `Pixel_3a_API_34_extension_level_7_x86_64`, serial
  `emulator-5554`, used only for development evidence.

## Implemented scope

- Original repository-owned CC0 procedural teacher with idle/blink, speaking, listening,
  thinking, encouraging expression, PCM energy, and six viseme shapes.
- Deterministic pure scene planner for café, supermarket, airport, and home.
- Closed scene/avatar wire contracts in Python, JSON Schema, and C#; arbitrary relative asset path
  negative fixture.
- Godot procedural catalog with 15 allow-listed object IDs, camera/lighting presets, fade,
  resource caching, old-tree cleanup, and predictable internal magenta fallback.
- Actual-WAV energy extraction at 40 ms; actual provider phonemes map to visemes, while missing
  timing remains an empty list with source `none`.

No external avatar/environment binary or new third-party dependency was added.

## Concurrent renderer/inference measurements

Command: `./scripts/benchmark.ps1 -Profile renderer`

Measurement window: 2026-10-12T19:36:06.8479815Z to 2026-10-12T19:36:09.5590876Z. The harness
verified that two real llama.cpp inference requests overlapped the renderer scene-tour window.

| Measurement | Result |
| --- | ---: |
| Café initial build | 243 µs |
| Supermarket initial build | 878 µs |
| Airport initial build | 771 µs |
| Home initial build | 1,210 µs |
| Scene transitions | 370.550–376.994 ms |
| Frame time p50 / p95 | 33.333 / 33.459 ms |
| Cached café revisit build | 436 µs |
| Cache resources / revisit growth | 68 / 0 |
| Godot reported video memory before tour | 21,582,543 bytes |
| Godot reported video memory before / after revisit | 21,900,307 / 21,900,307 bytes |
| Renderer working set / observed peak | 257,417,216 / 257,425,408 bytes |
| Avatar process overhead average | 27.826 µs/frame |
| Software VP8 mean / p50 / p95 / max | 5.993 / 5.904 / 6.640 / 6.967 ms/frame |
| VP8 frames / packets | 20 / 20 |
| Qwen request latencies | 1,164.858 ms; 376.323 ms |
| llama.cpp working set / peak | 2,690,437,120 / 3,207,290,880 bytes |
| System GPU memory used before / after | 5,488 / 5,489 MiB |

The avatar timeline used for the isolated overhead measurement is explicitly synthetic; it
measures renderer cost only. Real lip-sync evidence is separate below. Encoding used
`libvpx-vp8-software` through pinned PyAV while reading the live renderer shared-memory frames.
`hardware_encoding=false`; this is not Windows hardware-encoder evidence.

Godot's static-memory API returned zero in the exported runtime, so the report marks that API
unavailable and records `null` rather than treating zero as real memory use. The process working
set and Godot RenderingServer video-memory counter are the usable measurements. The `nvidia-smi`
values are system-wide snapshots with the model and renderer active, not renderer-exclusive VRAM.

## Functional/runtime evidence

- `./scripts/renderer-scene-smoke.ps1` captured four visually inspected, distinct PNGs under the
  ignored `.cache/renderer-scene-tour/` directory. Each contains the stylized teacher in the
  expected café, supermarket, airport, or home layout. The final run reported zero visual
  fallbacks and zero cache/video-memory growth on revisit.
- `./scripts/emulator-speech-smoke.ps1` launched real Kokoro, the host, and Godot. Godot logged
  `energy=51`, `visemes=23`, `duration_us=2038666`, and
  `source=provider_phoneme_alignment`; Android completed model-timed highlighting, isolated-word
  playback, and 0.75× replay. Cleanup stopped the app, renderer, servers, and reverse mappings.
- The fake-provider emulator renderer smoke uses `viseme_source=none`, requires nonempty PCM energy
  and zero viseme cues, and exercises Godot-to-aiortc video plus microphone return/reconnect.
- Pure planner tests assemble all four recipes, reject unrecognized scenarios and invalid timing,
  prove energy comes from PCM sample positions, and emit no visemes without provider timing.
- Godot self-test directly exercises the predictable internal missing-asset fallback. Unknown wire
  asset IDs/paths are rejected before this point.

## Transient failures and corrections

- The first narrow lint run found import ordering; Ruff fixed it and the complete Python gate
  passed afterward.
- The first scene-tour wrapper observed a blank `Start-Process.ExitCode` even though Godot produced
  every capture and pass marker. The harness was changed to use the bounded completion/report
  contract and then passed repeatedly.
- One renderer media smoke sampled the short process before its first shared-memory frame and
  failed with zero observed frames; the immediate repeat passed with changing frames and audio.
  This did not recur in the scene tour or emulator integration.
- Managed network restrictions prevented NuGet vulnerability metadata lookup during a Godot build;
  compilation completed with zero errors. The final Python dependency audit is recorded in the
  milestone status.
- The first final pre-commit attempts hit the managed global uv-cache permission and then sandbox
  network denial. Workspace-local uv/pre-commit caches plus the command-scoped Git safe-directory
  setting resolved permissions; the approved-network rerun fetched pinned hooks and every hook
  passed.

## Limits

The four proof images and short timing sample establish deterministic assembly and bounded revisit
behavior on this development machine; they are not a long-run leak or target-hardware claim. No
physical phone, intended Wi-Fi path, Windows hardware encoder, physical Android decoder, acoustic
test, monitor-off/unfocused run, thermal measurement, packet-loss study, or 30-minute soak was
executed. All remain mandatory Milestone 9 acceptance work.
