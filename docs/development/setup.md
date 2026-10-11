# Development setup

## Windows prerequisites

- PowerShell 7 or Windows PowerShell 5.1
- Git
- `uv`
- Android Studio or JDK 17
- Android SDK Platform 34, Build Tools 34.0.0, and Platform Tools
- .NET 8 SDK (the bootstrap script installs a repository-local copy when absent)
- Godot 4.7.2 .NET and matching export templates for renderer work; the bootstrap script installs
  pinned, checksum-verified portable copies into `.tools`

Run:

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi
./scripts/test.ps1 -Scope fast
```

`bootstrap.ps1` keeps downloaded Python/.NET/Gradle state in ignored `.tools` and `.cache`
directories and writes ignored `apps/android/local.properties`. Use `-IncludeMedia` to install the
Milestone 1 Python WebRTC dependencies and `-IncludeRenderer` for the Godot editor/export
templates. `-NoDownload` verifies an already-populated offline checkout. Godot requires no account
or license activation. `-IncludeLocalAi` downloads checksum-pinned llama.cpp/whisper.cpp runtimes,
the selected Qwen3 4B and comparison 1.7B models, the multilingual Whisper small model, and two
human-speech benchmark fixtures. The model files are ignored and are not part of this repository.

If Git reports dubious ownership in a managed checkout, use the command-scoped `safe.directory`
example in `AGENTS.md`; do not modify global configuration automatically.

## Android Studio emulator

Start the `Pixel_3a_API_34_extension_level_7_x86_64` AVD from Android Studio's Device Manager,
then route the loopback development port and install the current APK:

```powershell
adb reverse tcp:8765 tcp:8765
adb reverse tcp:8766 tcp:8766
adb install -r apps/android/app/build/outputs/apk/debug/app-debug.apk
```

Build the renderer and start the combined fake control/renderer stack:

```powershell
./scripts/build.ps1 -Target renderer
./scripts/dev.ps1 -Mode mock
```

Start the media server separately with `scripts/media-dev.ps1` and a fresh development token. Use
`127.0.0.1:8765` for control and `127.0.0.1:8766` for media in the debug app. The release manifest
still rejects cleartext; this is the supported emulator development path only. It does not satisfy
the physical-device/Wi-Fi release acceptance bundle scheduled for Milestone 9.

For the full Milestone 3 loopback stack, build the renderer and run:

```powershell
./scripts/dev.ps1 -Mode local -PairingToken '<at-least-32-random-characters>'
```

This starts the pinned Qwen3 4B model with llama.cpp on port 8767, renderer-backed media on 8766,
Godot, and the host on 8765. It stops child processes when the foreground host exits. Control is
still unauthenticated and all services deliberately remain loopback-only; use `adb reverse` for
emulator development. The 150 ms response marker is diagnostic audio, not teacher speech.
An alternate GGUF can be supplied with `-LlamaModelPath` together with an accurate
`-DialogueProviderId`; `-ContextSize` and `-GpuLayers` are also configurable. The selected pinned
4B model remains the default and alternate models require their own evaluation record.

Run the reproducible local model/STT comparison with:

```powershell
./scripts/benchmark.ps1 -Profile local-ai
```
