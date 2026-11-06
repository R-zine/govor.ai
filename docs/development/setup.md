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
uv run --frozen pre-commit install --install-hooks
```

For a first deterministic development run without model weights, omit `-IncludeLocalAi`.
The [README](../../README.md#develop-locally) walks through both modes. Ensure SDK Platform Tools'
`adb` is on PATH, or invoke it by its full path.

`bootstrap.ps1` keeps downloaded Python/.NET/Gradle state in ignored `.tools` and `.cache`
directories and writes ignored `apps/android/local.properties`. Use `-IncludeMedia` to install the
Milestone 1 Python WebRTC dependencies and `-IncludeRenderer` for the Godot editor/export
templates. `-NoDownload` verifies an already-populated offline checkout. Godot requires no account
or license activation. `-IncludeLocalAi` downloads checksum-pinned llama.cpp/whisper.cpp runtimes,
the selected Qwen3 4B and comparison 1.7B models, the multilingual Whisper small model, two
human-speech benchmark fixtures, Kokoro v1.0, and the Bulgarian Piper voice. The model files are
ignored and are not part of this repository.

If Git reports dubious ownership in a managed checkout, use the command-scoped `safe.directory`
example in `AGENTS.md`; do not modify global configuration automatically.

The installed pre-commit hook runs repository hygiene checks and selects component/consumer tests
from staged paths, including deletions and renames. It requires only the toolchains for those
applications: Python-only changes do not require Java or Godot. Documentation-only commits skip
software suites; hardware and benchmark commands are never selected implicitly. Preview a commit
with `./scripts/pre-commit-tests.ps1 -Staged -ListOnly`. The complete
[selection rules](commands.md) explain shared-boundary checks and dependency audits.
CI runs the same suites in dedicated platform jobs and skips the Windows-local dispatcher and
PowerShell parser hooks in its separate Linux pre-commit hygiene job.

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

Start the media server separately with a fresh development token:

```powershell
$devToken = [Guid]::NewGuid().ToString('N')
$devToken
./scripts/media-dev.ps1 -PairingToken $devToken -BindHost 127.0.0.1 -Source Renderer -AllowInsecureDevLan
```

The script requires the explicit cleartext opt-in even with a loopback bind. Use
`127.0.0.1:8765` for control and `127.0.0.1:8766` for media in the debug app. The release manifest
still rejects cleartext; this is the supported emulator development path only. It does not satisfy
the physical-device/Wi-Fi release acceptance bundle that later passed separately in Milestone 9.

The debug APK must first be built with `./scripts/build.ps1 -Target android`; building the renderer
alone does not create it. Use `adb -e` when only the emulator should be targeted.

For the full Milestone 3 loopback stack, build the renderer and run:

```powershell
./scripts/dev.ps1 -Mode local -PairingToken '<at-least-32-random-characters>'
```

This starts the pinned Qwen3 4B model with llama.cpp on port 8767, renderer-backed media on 8766,
Godot, and the host on 8765. It stops child processes when the foreground host exits. Control is
still unauthenticated and all services deliberately remain loopback-only; use `adb reverse` for
emulator development. Local teacher turns use Kokoro for `en-GB`/`en-US`, Piper for `bg-BG`, and
the process-isolated eSpeak NG fallback when a neural provider is unavailable.
An alternate GGUF can be supplied with `-LlamaModelPath` together with an accurate
`-DialogueProviderId`; `-ContextSize` and `-GpuLayers` are also configurable. The selected pinned
4B model remains the default and alternate models require their own evaluation record.

Run the reproducible local model/STT comparison with:

```powershell
./scripts/benchmark.ps1 -Profile local-ai
./scripts/benchmark.ps1 -Profile speech
./scripts/emulator-speech-smoke.ps1
```

The speech benchmark writes non-sensitive generated samples under `.cache/speech-samples` for a
brief listening check. The emulator smoke uses diagnostic WebRTC media plus real control-channel
teacher speech, then force-stops the app and both servers. It is development evidence only; it does
not replace the separately completed Milestone 9 physical-phone/acoustic acceptance.
