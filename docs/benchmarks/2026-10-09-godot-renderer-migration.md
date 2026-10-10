# 2026-10-09 Godot renderer migration and development proof

This is a repository/toolchain/local-runtime/emulator evidence record. It is not a physical-device
benchmark and contains no physical Wi-Fi, hardware-codec, acoustic, latency, resource, thermal, or
soak result.

## Environment

- Timestamp: 2026-10-09, Europe/Kiev (UTC+03:00).
- Windows process build: 10.0.26200.
- GPU: NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94.
- Engine: Godot 4.7.2 stable .NET, official build `ed1daf0bf`.
- Android development device: Android Studio API 34
  `Pixel_3a_API_34_extension_level_7_x86_64`, ADB serial `emulator-5554`.
- Transport: loopback aiortc server exposed to the emulator only through
  `adb reverse tcp:8766 tcp:8766`.

The editor ZIP and export-template TPZ are downloaded to ignored repository-local directories.
Bootstrap verifies these published SHA-512 digests before extraction:

- editor: `79229fd112b0c9cbeab82363a4ef7be18ea70f1caf86bf912789335b136fbe7e01db0053a33461438c5da1c680c17bbb10040bd09bedc51221cd4423d0367757`
- templates: `bb5c41d72370ed743660361f6228006f808ab04ca33abdc545d740b044f3fe057f32ae8cb7873a1bc86ddcd82ae683b9f6dfdfe4179852f2c0f1acde2ff6bd5a`

No engine account, license activation, or paid service was used.

## Implemented path

```text
Godot 1280x720 SubViewport -> synchronous RGBA readback -> latest-frame named mapping
Godot application PCM     -> 48 kHz mono blocks          -> bounded named-mapping ring
named mappings            -> aiortc VP8/Opus             -> native Android libwebrtc
Android hold-to-talk      -> WebRTC audio                -> aiortc receiver
```

The named mappings are Windows process-local transport. aiortc remains the only network-facing
media component. The renderer does not own signaling, pairing, lesson policy, providers, or
learner data.

## Commands and results

| Command/check | Result |
| --- | --- |
| `./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -NoDownload` | passed using the already checksum-verified local editor/templates and locked dependencies |
| `./scripts/test.ps1 -Scope godot` | passed: headless import, C# build with 0 warnings/0 errors, and `GOVOR_GODOT_SELF_TEST_PASS` |
| `./scripts/build.ps1 -Target renderer` | passed: Windows player exported |
| `./scripts/renderer-smoke.ps1` | passed muted: 5 complete frames, 5 distinct hashes, RGB maximum 255, 9 PCM blocks, peak 2621, proof PNG, tone-complete marker, clean exit, empty stderr |
| `./scripts/renderer-smoke.ps1 -Audible` | passed once under supervision; PC tone stopped after two seconds and the renderer exited |
| reader-started-before-writer probe | passed: named mappings recovered when the Godot writer started after the Python reader |
| `./scripts/emulator-renderer-smoke.ps1` | passed: fresh token, native connection, non-black Godot video and PCM observed by aiortc, Android first-render/1280x720 callbacks, reverse microphone frame, bounded cleanup |
| `./scripts/test.ps1 -Scope all` | passed after migration: 17 Python tests at 94.51% branch coverage, 3 Kotlin tests, 2 C# tests, 10 media tests, Godot gate, Android APK build |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit-final` | passed: no known vulnerabilities found |
| pre-commit over tracked and untracked sources | passed on the final clean pass after normalizing generated line endings |

The successful emulator server log recorded:

```text
Received first client microphone frame: sample_rate_hz=48000 samples=960
Received first renderer audio block: sample_rate_hz=48000 samples=960 peak=2621
Received first renderer video frame: width=1280 height=720 rgb_min=0 rgb_max=255
```

Android libwebrtc reported `Reporting first rendered frame` and a frame-resolution change to
1280x720. After startup, one callback interval reported 120 frames received/rendered with zero
drops over 4.001 seconds (30.0 fps). Disconnect/reconnect then produced a second non-black Godot
frame and second 48 kHz/960-sample microphone return. The remote-track end caused no unobserved
task exception, and the new peer did not replay the tone block retained in the bounded ring after
the two-second source ended.

The virtual decoder used by this AVD is `c2.goldfish.vp8.decoder`; it is not physical
hardware-decoder evidence. The short callback interval overlaps no controlled load and is not a
physical cadence or performance benchmark.

## Artifacts

- Exported player: `apps/renderer/Builds/Windows/GovorRenderer.exe`
  - size: 109,372,928 bytes
  - SHA-256: `65d86d986f0f5508a2dede1bce653bfb21fc6fd8cf06aed43872c0806e679175`
- Local proof image: `.cache/godot-renderer-proof.png` (ignored).
- Local runtime logs: `.cache/godot-player.stdout.log` and
  `.cache/godot-player.stderr.log` (ignored).
- Emulator server/renderer/WebRTC logs: `.cache/godot-emulator-*.log` (ignored).
- Emulator screenshot: `.cache/godot-emulator-connected.png` (ignored).
- Android UI hierarchy: `.cache/godot-emulator-window.xml` (ignored).

The local proof image was visually inspected and contains the cyan capsule, ground, lighting, and
dark-blue background. The emulator screenshot shows the connected controls but a black video
region. ADB screencapture does not provide reliable evidence for this WebRTC `SurfaceView` in the
observed run: non-black pixels reached aiortc and Android emitted render callbacks, but the scene
pixels are absent from the screenshot. The screenshot is therefore inconclusive, not a passing
visual-scene artifact.

## Failures encountered and fixed

- The first export attempt allowed Godot to return success despite project/solution discovery
  errors. A solution file was added and the build wrapper now fails on an absent executable or an
  `ERROR:` line in the export log.
- The first runtime called camera look-at before the camera entered the scene tree. Scene creation
  now uses `LookAtFromPosition`; subsequent runtime stderr is empty.
- Initial UI automation tapped fixed screen coordinates and entered the token in the host field.
  The emulator script now derives field/button centers from the UI Automator hierarchy.
- The first emulator evidence logged an initial all-black publication. The aiortc check now waits
  for a non-black renderer frame, and the local probe fails if every RGB channel remains zero.
- The first renderer-source disconnect left aiortc's normal end-of-track exception unobserved.
  The microphone consumer now treats `MediaStreamError` as normal teardown, with a regression test.
- The first reconnect replayed one retained 20 ms tone block. New audio readers now start after
  the ring's current write position and emit silence until a genuinely new block is published.
- One sandboxed local smoke emitted Godot errors because its Windows user-data/certificate paths
  were denied. The same test passed with normal host access; this was an execution-environment
  restriction, not accepted as a renderer pass until rerun.

## Deferred Milestone 9 target-hardware work

- Physical Android video, audio, and microphone behavior.
- Trusted Wi-Fi rather than emulator loopback forwarding.
- Android hardware decode and Windows hardware encode selection.
- Frame cadence and end-to-end latency distributions.
- CPU, GPU, RAM, VRAM, thermal, and power measurements.
- Background/foreground lifecycle, renderer unfocused, and monitor-off checks.
- 30-minute stability/soak.

Milestone 1 is complete on the native-emulator development criteria adopted in ADR-0004, so
Milestone 2 may proceed. These emulator and local-runtime results do not close any Milestone 9
physical target-hardware acceptance row.
