# 2026-10-26 selectable teachers and photographic backdrops

## Scope

This record covers the post-milestone visual/voice presentation change on the development PC. It
does not replace the signed `0.1.11` Milestone 9 physical-phone acceptance. No phone, camera scan,
acoustic judgment, release package, hardware codec, or mixed Ethernet/Wi-Fi path was exercised.

## Environment

- Windows process build 10.0.26200, Europe/Kiev.
- NVIDIA GeForce RTX 3060, driver 560.94.
- Godot 4.7.2 stable .NET (`ed1daf0bf`) with repository-local export templates.
- Renderer: Compatibility/OpenGL 3.3, 1280x720, 30 fps.
- Voice tests: local deterministic/fake engine boundaries; the focused eSpeak test invoked the
  installed local worker. No paid/cloud speech request was sent.

## Assets and provenance

The renderer packages three Ara 3D Gen/MakeHuman-derived CC0 teachers. Ara was pinned to commit
`0c3473d7d46a2badcdcd1dcfd4aeb0762eb04b20`; the exact profile JSON and the Blender post-process
script are committed beside the artifacts. The distributed GLBs have one skinned mesh, 34 facial
blend shapes including 14 speech visemes, and no animation clip:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `elena.glb` | 8,823,800 | `0703ACEE2388EDCA7149DA23BED5CC36B5F3C1A64AF911120F15B8F4E6B68182` |
| `amira.glb` | 9,981,608 | `E6C4D41D01A743FCCECADD31490C157310DA52AEE2DAD157E6831A4B1F184DB8` |
| `daniel.glb` | 10,528,416 | `1BCDB7C2D1F549F2EEC1B1D92FC135FCC9B08E2C1A20F665D54E63B5DA7E0458` |

Four 1280-pixel-wide CC0 JPEG derivatives from Wikimedia Commons are packaged as 2D built-in
backdrops. Source pages/authors and exact hashes are in
`apps/renderer/Assets/Backdrops/README.md`. Godot imports embedded GLB images as Basis Universal;
the release does not create external texture files or retain Ara animation clips.

## Voice mapping

The closed profile ID is shared by the renderer and speech factory. Elena maps to Kokoro
`bf_emma`/`af_heart`, Amira to `bf_isabella`/`af_bella`, and Daniel to
`bm_george`/`am_michael` for `en-GB`/`en-US`. The installed Bulgarian Piper catalog exposes only
`bg_BG-dimitar-medium`, so Daniel uses Piper while Elena/Amira intentionally use eSpeak NG
`bg+f3`. Cloud-compatible profile voice names are configurable; mock transport tests verify the
dynamic selection without calling a cloud service.

## Commands and results

| Command/check | Result |
| --- | --- |
| `./scripts/test.ps1 -Scope csharp` | Passed: 10 C# contract tests. |
| `./scripts/test.ps1 -Scope godot` | Passed during implementation: import, C# build, and renderer self-test. |
| Focused host/speech/provider pytest selection | Passed: 46 tests. |
| `./scripts/build.ps1 -Target renderer` | Passed after adding Godot's explicit `--quit`; an earlier export wrote the complete player but left the Godot console waiting and was interrupted. |
| `./scripts/renderer-scene-smoke.ps1` | Passed: four distinct photo/profile captures, all with an open viseme; zero fallbacks and zero cache growth. |
| Exported-player `--ui-proof-image` check | Passed visually: opaque pre-connect screen contained `Teacher: Amira`. A project icon was supplied as a layout-only QR placeholder, so this is not QR decoding evidence. |

The final scene-tour report was written to ignored
`.cache/renderer-scene-tour/renderer-scene-tour.json`:

| Measurement | Result |
| --- | ---: |
| Profiles across cafe/supermarket/airport/home | Elena / Amira / Daniel / Elena |
| Captured viseme | `open` for all four |
| Frame count | 66 |
| Frame time p50 / p95 | 33.3333 / 132.4393 ms |
| Scene build times | 119 / 16,355 / 17,875 / 15,814 us |
| Transition times | 354,548 / 369,618 / 373,745 / 375,624 us |
| Cache growth on cafe revisit | 0 resources |
| Reported video-memory revisit delta | 124 bytes |
| Peak working set | 451,932,160 bytes |
| Avatar process average | 37.0076 us |
| Software VP8 packets | 20 |
| Software VP8 encode mean / p95 / max | 7.4068 / 9.7707 / 9.9693 ms |

The high p95 render-frame value occurs while swapping/importing the larger teacher resources in
this short synthetic tour; it is not a steady-state cadence result. The tour's bounded cache and
video-memory revisit checks passed. No hardware-encoding claim is made.

## Final regression gates

| Command | Result |
| --- | --- |
| `./scripts/test.ps1 -Scope all` | Passed: 291 Python tests at 85.27% coverage, Kotlin/JVM tests, 10 C# tests, 21 media tests, Godot import/build/self-test, and Android debug assembly. |
| `uv run --frozen pip-audit` | Passed: no known vulnerabilities. |
| `uv run --frozen pre-commit run --all-files` | Passed: all hygiene, secret/large-file, Ruff, contract, PowerShell, and affected-application test hooks. |

The all-scope run emitted the existing Starlette `httpx` deprecation and local pytest-cache access
warnings. The Godot C# build could not query NuGet's vulnerability service in the restricted test
environment, but compiled with zero errors; the independent Python dependency audit succeeded.

## Limitations

- The host selector is available only in the pre-connect state; it intentionally cannot change
  model/voice halfway through a spoken lesson turn.
- The female Bulgarian presentation is deterministic and local but less natural than Piper.
- Cloud voice labels are configuration names, not guaranteed gender metadata from every compatible
  provider.
- The photographs are static 2D backdrops. Installed patchable environments remain simple 3D
  primitives; arbitrary image/model packs are still rejected.
- Current screenshots and metrics are development-PC evidence. The new assets have not traversed a
  signed package or physical Android device.
