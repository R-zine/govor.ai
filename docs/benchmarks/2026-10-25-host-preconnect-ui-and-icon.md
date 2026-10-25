# Host pre-connect UI and icon verification - 2026-10-25

## Scope

This post-Milestone 9 maintenance check covers only the Windows host presentation added on top of
the already verified QR-first pairing flow:

- an opaque 2D state dedicated to connecting the Android client;
- same-network instructions, QR status/expiry, and a hidden manual fallback;
- protected bootstrap handoff without secret process arguments;
- transition to the 3D lesson at `session_started`; and
- a govor.ai project/window/executable icon in place of the Godot default.

It does not repeat or extend the completed physical-phone, Wi-Fi, acoustic, codec, performance, or
camera-focus acceptance. The QR remains outside the 1280x720 WebRTC capture viewport.

## Environment

- Windows process build 10.0.26200 on the documented RTX 3060 development/target PC.
- Godot 4.7.2 stable .NET (`ed1daf0bf`) with repository-pinned editor/export templates.
- NVIDIA driver 560.94; windowed proof used the Compatibility renderer/OpenGL 3.3.
- No PC audio was requested or played; every proof used `--no-startup-tone`.

## Implementation evidence

- `HostPairingScreen` owns the full-window connection presentation. The underlying lesson
  `SubViewport` is covered locally but remains a separate renderer-neutral media source.
- The strict C# bootstrap parser rejects unknown fields and malformed endpoints, code,
  fingerprint, or expiry. The renderer self-test covers a valid payload and closed-field failure.
- The launcher writes the identical bounded JSON bootstrap and QR atomically under its protected
  per-user security directory, passes only file paths to Godot, and removes both files at shutdown.
- `session_started` calls `CompleteConnection`, which hides the 2D screen and restores input to the
  3D lesson.
- `project.godot` uses the transparent source PNG; the Windows export uses a seven-entry
  16/24/32/48/64/128/256-pixel ICO. The packaged executable reports product name `govor.ai` and
  description `Private local English tutor`.

## Commands and results

| Command/check | Result |
| --- | --- |
| `uv run --cache-dir .cache/uv-qr --frozen pytest apps/launcher/tests/test_pairing_qr.py apps/launcher/tests/test_cli.py -q` | Passed, 17 tests |
| `./scripts/test.ps1 -Scope godot` | Passed project import, C# build, strict bootstrap self-test, and headless renderer self-test |
| `./scripts/build.ps1 -Target renderer` | Passed after rerunning with normal Windows user-data access |
| Exported renderer with `--no-startup-tone --pairing-qr=... --pairing-bootstrap=... --ui-proof-image=... --exit-after-ui-proof` | Exited 0; captured the default 2D screen |
| Same command plus `--show-manual-pairing` | Exited 0; captured the manual fallback dialog |
| Windows associated-icon extraction from exported and packaged `GovorRenderer.exe` | 32x32 branded icon returned; product metadata matched govor.ai |
| `./scripts/test.ps1 -Scope all` | Passed: 268 Python tests/85.18% coverage, Android/JVM tests, 9 C# tests, 21 media tests, Godot self-test, Android debug build |
| `./scripts/package.ps1 -Version '0.1.16' -VersionCode 17 -GradleUserHome '.cache/gradle' -GradleOffline -NoArchive` | Passed Godot export, Android release lint/build, v2 signing, embedded-runtime import, source, and prerequisite checks |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-host-preconnect` | No known vulnerabilities |
| `uv run --frozen pre-commit run --all-files` with repository-local pre-commit home and safe-directory environment | Passed every hook, including contracts, PowerShell syntax, and affected-app tests |
| `./scripts/pre-commit-tests.ps1` with the changed launcher/renderer paths after the last helper edit | Passed the Python gate (268 tests/85.18%) and Godot gate |

The first sandboxed renderer export produced the executable but was correctly rejected by the
wrapper because Godot could not open `user://`; rerunning with ordinary Windows user-data access
passed. A diagnostic headless screenshot attempt used Godot's dummy rendering backend and could
not yield textures; its single spawned renderer was stopped, then the intended hidden-window proof
completed. These are tooling-environment failures, not passing runtime evidence.

Two complete all-files pre-commit runs passed. A later redundant all-files rerun passed every
static/contract hook but its wrapper remained waiting after the captured affected-app child had
exited and no child process remained; that run was interrupted after process/lock inspection. The
affected-app hook was then invoked directly with the final changed launcher/renderer paths and
passed both selected scopes. No result from the stalled wrapper is counted as passing evidence.

## Visual and artifact evidence

| Artifact | Bytes | SHA-256 | Observation |
| --- | ---: | --- | --- |
| Ignored `.cache/host-preconnect/screen.png` | 123,603 | `4822676f425151618cdcac04826b9f1bb7a8735460cea617d753d3c2bbb65b82` | 1280x720 opaque instructions/QR/countdown screen; no 3D visible |
| Ignored `.cache/host-preconnect/manual.png` | 108,483 | `94556fdead999baf829ae248709f0b596aa1ec5d309169ca48ec0af93e607577` | Dimmed fallback modal with hosts, code, fingerprint, copy and close actions |
| `apps/renderer/Assets/Brand/govor-icon.png` | 414,085 | `4d5046dc45191d6e9ad2d1c1b7aac95ee590ca10a5a95729402e55efa8a8af0c` | Transparent project-owned mint speech/wave mark |
| `apps/renderer/Assets/Brand/govor-icon.ico` | 37,364 | `486536d63343bcdffb958ab35aca7473536cf03d02581edd5737d76681ad09b1` | Valid type-1 ICO with seven resolutions |
| Exported `GovorRenderer.exe` | 109,407,744 | `a2797abfd708574b979aa07ae655c4a2260a254328ed7917abb110c8d87e4351` | Associated icon extraction returned the branded mark |
| Ignored signed `govor.ai-0.1.16-android-release.apk` | 59,891,893 | `c0639ae3d5c4ba02f217616e41c0eb600ffe90aae262c9aacb8477e2f325edf3` | Package companion; Android code is unchanged in this follow-up |

## Evidence boundary and cleanup

- The screenshots prove the exported Windows renderer's local UI layout, not physical camera
  focus or phone scanning. Segno-to-ZXing data compatibility remains covered by the existing JVM
  test; the prior real-camera limitation remains recorded.
- No new LAN, discovery, signaling, media, microphone, or Android behavior is claimed.
- No tone was enabled. At completion no `GovorRenderer`, `llama-server`, or port 8765-8768 listener
  from this check remained. The two observed Python processes were VS Code's Black formatter
  language server, not govor.ai services.
