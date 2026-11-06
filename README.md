# govor.ai

Practice spoken English with a patient virtual teacher, with Bulgarian help when you need it.

govor.ai is an open-source MVP for a Windows PC and an Android phone. The PC runs the AI models
and renders the teacher; the phone plays the lesson and captures your voice. Everything runs on
your own devices by default. After the initial downloads, lessons work without internet access.

You listen to a question, hold the microphone button to answer, and continue the conversation.
If you get stuck, ask in Bulgarian. The teacher can explain, repeat, or help you phrase an answer
before returning to English.

## What it supports

| Area | Features |
| --- | --- |
| Speaking practice | Push-to-talk answers, Bulgarian help requests, mixed English/Bulgarian explanations, and local AI assessment of an answer's meaning |
| Listening and pronunciation | British or American English, replay, slower/faster playback, interactive subtitles, word replay, IPA, and pronunciation explanations |
| Guided lessons | Café, supermarket, airport, and home scenarios; difficulty adaptation; lesson progress/completion; saved progress and resume |
| Your own lessons | Generate a lesson from a topic on the phone or PC, with optional difficulty, environment, and length; import JSON or multi-lesson ZIPs; confirm deletion from an active lesson |
| Live content updates | Imported/generated lessons appear without restarting; lesson generation status survives phone lock/reconnect |
| Teacher and scenes | Three selectable 3D teachers, photographic backdrops, lip movement driven by real audio and available phoneme timing, and data-only environment ZIP imports |
| Connection | QR pairing, a manual fallback, saved-host reconnect, and encrypted release connections over the home network |
| Local ownership | Offline local AI by default, SQLite progress, history export/deletion, and optional developer-configured cloud providers |
| Updates | Full portable releases and signed offline application patches; a patch may also carry an Android update for normal installation |

This is an MVP rather than a general-purpose language tutor. Recognition and grading can be
wrong, especially with short or hesitant Bulgarian speech. It does not score pronunciation or
support talking over the teacher. Word highlighting uses provider timing when available; missing
timing does not stop playback. Bulgarian female voice presentation currently uses pitch-adjusted
Piper speech rather than a separately trained female voice.

## Use the app

### What you need

- A 64-bit Windows PC. The tested target is an NVIDIA RTX 3060-class machine; other hardware has
  not been broadly qualified. The PC performs the rendering and AI work.
- An Android phone running Android 8.0 or later, with a microphone and Wi-Fi.
- Both devices on the same trusted home network. The PC can use Ethernet or Wi-Fi; the phone
  uses Wi-Fi. Guest networks with device isolation will not work.
- Internet for first-time setup and room for the application plus approximately 3.4 GB of models.

Use a matching **Windows portable ZIP** and **signed Android release APK** supplied by a
maintainer. GitHub's source-code ZIP is a developer checkout, not the installed application. If
prebuilt artifacts are unavailable, see [Build a release](#build-a-release).

### Set up the PC

1. Extract the entire Windows ZIP into a writable folder, such as `Documents\govor.ai`.
2. Open that folder and double-click **Setup-Govor.cmd**. Accept the Microsoft Visual C++ runtime
   prompt if needed. Wait for the model downloads and integrity checks to finish.
3. Double-click **Start-Govor.cmd**. Allow the packaged runtime through Windows Firewall on your
   trusted home network. A Private Windows network profile is easiest to configure.
4. Leave the console and host window open. The host shows instructions and a pairing QR.

The portable package includes its own runtimes. Learners do not need development tools.

### Set up the phone and connect

1. Copy/download the signed APK to the phone and open it. If Android asks, permit installation
   from that particular browser/file manager, then install. Device/region policies may add steps;
   follow the phone's supported installation flow.
2. Open **govor.ai**, choose **Scan host QR**, and grant camera permission when requested.
3. Scan the QR on the PC. Choose a teacher/lesson and start. Grant microphone permission when
   requested, then hold the talk button while speaking and release it to send your answer.

On later visits, start the PC host and choose **Reconnect to saved host** on the phone. Keep the
PC awake and the host running during a lesson. To stop the host, press Enter in its console and
wait for cleanup. Normal lessons need only the local network, not internet access.

Detailed help: [Windows guide](docs/user-guide/windows.md),
[Android guide](docs/user-guide/android.md), and [troubleshooting](docs/troubleshooting/README.md).

### Add content and install updates

The phone's lesson selector has **Create a lesson**. The host's **Content & updates** menu also
provides lesson creation, JSON/ZIP lesson import, environment ZIP import, and application patching.
Generated lessons use the running local model; the optional settings can be left on automatic.
Environment packs currently contain validated procedural scene recipes, not new models or code.

Models, progress, pairing state, and logs live under `%LOCALAPPDATA%\govor.ai`. Custom lessons and
environment recipes live in the installation's `content\lessons` and `content\environments`.
Preserve those content folders when replacing a whole Windows release. Signed patches preserve
unlisted content. Install Android updates over the existing app using the same signing identity;
uninstalling first removes its saved pairing state.

## Develop locally

Windows is the supported environment for the complete host/renderer stack. Individual domain,
contract, and Android modules have their own tests, but that does not establish another host OS.

### Prerequisites

Install [Git](https://git-scm.com/downloads), [uv](https://docs.astral.sh/uv/getting-started/installation/),
and [Android Studio](https://developer.android.com/studio). In Android Studio's SDK Manager install
Android SDK Platform 34, Build Tools 34.0.0, and Platform Tools. Configure JDK 17 for Gradle.
Put Platform Tools' `adb` on PATH, or invoke it by its full path. Use PowerShell 5.1 or later.

Bootstrap obtains Python 3.12 through uv, restores the pinned Gradle/NuGet dependencies, installs
a local .NET 8 SDK if needed, and can download Godot 4.7.2 **.NET** plus matching export templates.
Godot does not require an account or license activation.

Clone this repository, open PowerShell in its root, then run:

```powershell
# Toolchains and media dependencies, without downloading AI model weights.
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer
uv run --frozen pre-commit install --install-hooks

# Check the code, then build the debug Android app and exported renderer.
./scripts/test.ps1 -Scope fast
./scripts/build.ps1 -Target all
```

Downloaded tools, models, and build caches stay in ignored `.tools` and `.cache` directories.
The bootstrap creates the ignored `apps/android/local.properties` for your SDK location.
For an already populated offline checkout, add `-NoDownload`.

### Try a deterministic development lesson

Create and start an API 34 emulator in Android Studio's Device Manager. With one emulator running:

```powershell
adb -e reverse tcp:8765 tcp:8765
adb -e reverse tcp:8766 tcp:8766
adb -e install -r apps/android/app/build/outputs/apk/debug/app-debug.apk
```

Start the fake lesson/control host and renderer in one terminal:

```powershell
./scripts/dev.ps1 -Mode mock
```

Start renderer-backed media in a second terminal:

```powershell
$devToken = [Guid]::NewGuid().ToString('N')
$devToken  # Enter this development token in the debug phone app.
./scripts/media-dev.ps1 -PairingToken $devToken -BindHost 127.0.0.1 -Source Renderer -AllowInsecureDevLan
```

In the debug app use media `127.0.0.1:8766`, control `127.0.0.1:8765`, and that token. Connect and
start a lesson. This mode uses scripted responses and brief diagnostic audio, not real AI speech.
Stop both terminals with Ctrl+C afterward. The cleartext opt-in flag is required by the media
script even with the explicit loopback bind above.

### Run the real local models

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi
$devToken = [Guid]::NewGuid().ToString('N')
$devToken
./scripts/dev.ps1 -Mode local -PairingToken $devToken
```

Use the same emulator reverse mappings and debug connection fields. Local mode starts the model,
media, renderer, and control processes together; it uses the exported renderer built above.
Ctrl+C stops the managed development processes. This bootstrap downloads several GB, including a
comparison model and speech test fixtures in addition to the release models.

Development control is loopback-only and has no release authentication/TLS lifecycle. The debug
APK permits cleartext for these checks. Use a signed release for an actual home-network setup.

See [development setup](docs/development/setup.md) for SDK paths, provider configuration, and
[cloud privacy controls](docs/privacy/cloud-providers.md) before enabling any external provider.

### Tests

```powershell
./scripts/test.ps1 -Scope all
uv run --frozen pre-commit run --all-files
```

For a focused change, scopes include `python`, `contracts`, `kotlin`, `csharp`, `speech`, `media`,
and `godot`. Installed commit hooks choose component tests and their consumers from staged paths,
including deletions/renames, and run linting/static checks. Preview the selection with
`./scripts/pre-commit-tests.ps1 -Staged -ListOnly`; see [the rules](docs/development/commands.md).
Documentation-only commits skip application tests. Physical-device tests
and performance benchmarks are separate, explicit commands; ordinary unit tests need no model
weights or physical phone. See [testing strategy](docs/testing/strategy.md).

### Build a release

The release packager builds a signed APK, exports Godot, embeds the Python/local-service
runtimes, and includes documentation, license notices, and source materials. Public binary
distribution still has the open items recorded in the
[release licensing review](distribution/OPEN_SOURCE_RELEASE.md); a successful build alone does
not close those items.

For your own local release build, initialize private signing keys once, then choose a version and
an Android version code higher than the previous build you are updating. For example:

```powershell
./scripts/initialize-release-signing.ps1
./scripts/package.ps1 -Version 0.2.0 -VersionCode 26
```

Artifacts go under `.cache/dist`: a Windows ZIP, signed APK, and SHA-256 artifact manifest.
The package command requires the local runtimes downloaded by `-IncludeLocalAi`. Back up your
ignored `.secrets` privately: the same Android key is needed for compatible updates, and the
application-update key signs `.govorpatch` files. Your independently signed APK cannot update
another maintainer's APK. Neither signing key belongs in a public repository or release.

## How it fits together

| Location | Responsibility |
| --- | --- |
| `apps/android` | Kotlin, Jetpack Compose Material 3, native WebRTC, audio, and microphone UI |
| `apps/host` / `apps/launcher` | Python/FastAPI orchestration, secure pairing, process ownership, and packaging entry points |
| `apps/renderer` | Godot .NET/C# teacher, scenes, animation, and local frame/audio output |
| `packages/domain` / `packages/progress` | Framework-independent teaching rules and SQLite persistence |
| `packages/contracts` | Versioned JSON Schema and validated Python, Kotlin, and C# messages |
| `services` | llama.cpp/Qwen, whisper.cpp, Kokoro/Piper/eSpeak, optional providers, and aiortc media |
| `docs` | User/developer guides, architecture, decisions, and dated verification records |

The renderer sends frames through a Windows-local bridge; aiortc owns WebRTC. Android performs
no AI inference or 3D rendering. The host keeps inference services on loopback and uses paired,
authenticated HTTPS/WSS and encrypted WebRTC media for release connections.

## Privacy, limitations, and contributing

Local providers and offline-only mode are the default. There is no required account, subscription,
telemetry, or cloud backend. Raw microphone recordings and full learner transcripts are not saved
by default. Optional cloud providers require explicit configuration, and microphone upload has a
separate consent gate. Read the [privacy guide](docs/privacy/cloud-providers.md) for the boundary.

This is one-PC/one-phone software for a trusted local network, not a public internet service.
The historical hardware acceptance record covers a particular PC/phone/release, not every device
or a blanket guarantee for later builds. Current results and known limits are in
[project status](docs/milestones/STATUS.md).

Bug reports, clearer lessons, accessibility improvements, and code contributions are welcome.
Describe the host/client versions, what you expected, and what happened. Share redacted logs;
keep recordings, private lessons, credentials, and signing keys out of issues and pull requests.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

Original govor.ai code, documentation, and lesson definitions are licensed under
**GNU GPL v3.0 or later**. See [LICENSE](LICENSE) and [COPYRIGHT](COPYRIGHT). Contributions use the
same license unless explicitly agreed otherwise.

Dependencies, separately downloaded models/voices, and CC0 character/backdrop assets retain their
own licenses. See [third-party licenses](THIRD_PARTY_LICENSES.md),
[asset provenance](apps/renderer/Assets/Teacher/Ara/README.md), and
[release licensing requirements](distribution/OPEN_SOURCE_RELEASE.md). Publishing the source and
redistributing a complete binary bundle have different requirements; the latter review is still
open for the native media stack and standalone Android notices.
