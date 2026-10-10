# 2026-10-09 superseded Unity renderer bridge implementation record

> Historical record only. ADR-0003 selected Godot 4.7.2 .NET later on 2026-10-09. All Unity source
> and active Unity commands were removed. Do not use this file as current-stack guidance.

This is a software verification record, not a performance benchmark or Unity runtime result. The
Unity editor had no active license, so no renderer process produced frames or PCM during this work.

## Environment and intended path

- Windows process build: 10.0.26200.
- GPU inventory: NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94. No GPU behavior was measured.
- Unity editor installation: 2022.3.62f1 (`4af31df58517`).
- Android target available for later development: API 34 emulator `emulator-5554`; not exercised
  by the renderer bridge in this record.
- Intended path: Unity `RenderTexture` -> asynchronous 1280x720 RGBA readback -> Windows-local
  named mapping -> aiortc video track -> native Android libwebrtc.
- Intended audio path: Unity-owned 48 kHz mono PCM -> bounded ring of 20 ms blocks -> aiortc Opus
  path -> native Android audio. Missing PCM produces silence, not a persistent diagnostic tone.

## Protocol and resource bounds

| Item | Implemented bound |
| --- | --- |
| Video surface | 1280x720 RGBA, 3,686,400-byte latest-frame payload |
| Video queue | One publication; stale frames are replaced |
| Audio format | PCM signed 16-bit little-endian, mono, 48 kHz |
| Audio block | 960 samples / 20 ms / 1,920 payload bytes |
| Audio ring | 64 blocks / 1.28 seconds maximum retained audio |
| Process transport | Named memory mappings in the current Windows session; no bridge socket |
| Consistency | Odd/even video publication sequence; per-slot audio sequence |
| Restart | Random writer generation resets consumer sequence state |

The video path necessarily includes GPU-to-CPU readback and managed copies before aiortc encoding.
Its cadence, CPU/GPU cost, latency, and hardware-encoder eligibility are unknown until the licensed
player runs; the table above is configuration, not measurement.

## Commands and results

| Command/check | Result | Evidence limit |
| --- | --- | --- |
| `./scripts/test.ps1 -Scope media` | pass: strict mypy, 9 tests | Includes byte-buffer protocol tests and real aiortc loopback; not Unity runtime |
| Renderer named-mapping open/close smoke through `RendererBridgeSource` | pass | Proves Python can allocate the production-sized named mappings on Windows only |
| `./scripts/test.ps1 -Scope unity` | partial: runtime C# compile passed | Editor produced no test XML; licensing IPC timed out after 60 seconds; Unity returned 199 |
| `./scripts/test.ps1 -Scope all` | pass | 17 Python, 3 Kotlin, 2 C#, 9 media tests, Android debug APK build |
| `uv run --frozen pip-audit --cache-dir .cache/pip-audit` | pass | No known vulnerabilities; final run had permitted network access |
| Pre-commit over tracked and untracked source files | pass | JSON/YAML, whitespace, secrets/size, Ruff, contract tests |
| Unity player build/launch | not executed | Blocked by inactive Unity license |
| Android emulator renderer check | not executed | No built/running Unity writer |
| Physical device/Wi-Fi/codecs/latency/soak | blocked/not executed | No physical phone and no verified renderer runtime |

Commands executed from the repository root included:

```powershell
./scripts/test.ps1 -Scope media
./scripts/test.ps1 -Scope unity
./scripts/test.ps1 -Scope all
. ./scripts/common.ps1
Initialize-GovorEnvironment
uv run --frozen pip-audit --cache-dir .cache/pip-audit
$env:PRE_COMMIT_HOME = Join-Path (Get-Location) '.cache\pre-commit-bridge'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = 'C:/Users/PC/Documents/GitHub/govor.ai'
$sourceFiles = @(git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' ls-files --cached --others --exclude-standard)
uv run --frozen pre-commit run --files $sourceFiles
```

The audit's first sandboxed attempts failed on the external default cache and denied network;
the exact final audit command above passed with approved network access and a repository-local
cache. Pre-commit's first attempts failed on Git dubious ownership and hook-cache/network setup.
The final run supplied command-scoped `safe.directory`, repository-local `PRE_COMMIT_HOME`, and
`git ls-files --cached --others --exclude-standard`; it passed without changing global Git config.

The final debug APK was unchanged at 58,607,581 bytes with SHA-256
`6716206a9e43188b0eaf1551d41f9af90fc424c26ecdfb83d2a60d38ffd2eced`.

The final cleanup check found zero Unity Editor processes, zero `GovorRenderer` processes, no
listener on port 8766, and no renderer executable artifact. No Unity scene or tone ran during this
work; the installed Unity Hub background process was left untouched.

## Required next measurement

This path is closed. Continue with the Godot commands in `apps/renderer/README.md`; do not attempt
to activate or rebuild the removed Unity project. The original planned next step had been to
launch the renderer and
`media-dev.ps1 -Source Renderer` on loopback with `adb reverse`. Record image orientation, delivered
resolution/cadence, the exact two-second audio window, reverse microphone frames, reconnect and
teardown, CPU/GPU/RAM/VRAM, codec selection, and process cleanup. Stop both processes immediately
after the audio check. None of those outcomes is inferred here.
