# Development commands

| Command | Purpose |
| --- | --- |
| `./scripts/bootstrap.ps1` | Install/validate pinned development dependencies |
| `./scripts/bootstrap.ps1 -IncludeMedia` | Also resolve Milestone 1 WebRTC experiment packages |
| `./scripts/bootstrap.ps1 -IncludeRenderer` | Install pinned Godot .NET editor and export templates |
| `./scripts/dev.ps1 -Mode mock` | Run loopback-only deterministic fake host |
| `./scripts/test.ps1 -Scope python` | Python lint, format, type, unit/integration, coverage |
| `./scripts/test.ps1 -Scope contracts` | JSON Schema and fixture tests |
| `./scripts/test.ps1 -Scope kotlin` | Core/app JVM tests, Android lint, and debug APK compilation |
| `./scripts/test.ps1 -Scope csharp` | Pure C# contract tests |
| `./scripts/test.ps1 -Scope media` | Real in-process WebRTC negotiation and bidirectional media tests |
| `./scripts/test.ps1 -Scope godot` | Godot headless import, C# build, and renderer self-test |
| `./scripts/test.ps1 -Scope all` | All tests, Godot validation, and debug APK build |
| `./scripts/test.ps1 -Scope hardware` | Milestone 9 physical-device release suite; never a mock or emulator substitute |
| `./scripts/pre-commit-tests.ps1 -ListOnly <paths...>` | Show the software test scopes selected for staged paths without running them |
| `./scripts/pre-commit-tests.ps1 -Staged -ListOnly` | Preview checks for the index, including deletions and renames |
| `./scripts/build.ps1` | Build Android debug and C# development artifacts |
| `./scripts/build.ps1 -Target renderer` | Export the local Godot Windows renderer |
| `./scripts/renderer-smoke.ps1` | Run a muted, bounded Godot frame/PCM/cleanup smoke check |
| `./scripts/renderer-scene-smoke.ps1` | Capture and measure all four validated scenes plus avatar/software encoding |
| `./scripts/emulator-renderer-smoke.ps1` | Development-only Godot/aiortc/native-emulator media and microphone check |
| `./scripts/benchmark.ps1 -Profile inventory` | Write environment inventory, not performance results |
| `./scripts/benchmark.ps1 -Profile renderer` | Measure scene/avatar/render/software-encode work concurrently with Qwen3 4B |
| `./scripts/progress.ps1 -Action View` | View local structured learner progress/settings as JSON |
| `./scripts/progress.ps1 -Action Export -OutputPath <path>` | Export structured progress; never audio/transcripts |
| `./scripts/progress.ps1 -Action Delete -ConfirmDelete` | Delete progress history while preserving settings |
| `./scripts/progress.ps1 -Action DeleteAll -ConfirmDelete` | Delete progress and restore settings defaults |
| `./scripts/provider-credentials.ps1 -Action Status -Target <name>` | Check a Windows Credential Manager provider target without revealing its secret |
| `./scripts/initialize-release-signing.ps1` | Create or retain the ignored ACL-restricted Android signing identity |
| `./scripts/package.ps1 -Version <semver> -VersionCode <integer>` | Export/sign/stage the release APK and portable Windows ZIP |
| `./scripts/m8-vm.ps1 -Action Prerequisites -IsoPath <iso>` | Check local QEMU/WHPX clean-Windows prerequisites |
| `./scripts/m8-vm.ps1 -Action Provision -IsoPath <iso> -IsoSha256 <sha256>` | Create the verified clean Windows base VM |
| `./scripts/m8-vm.ps1 -Action Start` | Start/create the disposable clean acceptance overlay |
| `./scripts/m8-vm.ps1 -Action StageRelease -Version <semver>` | Hash, copy, and extract the candidate inside the VM |
| `./scripts/m8-vm.ps1 -Action SetupRelease` | Run the packaged setup wrapper inside the clean VM |
| `./scripts/m8-vm.ps1 -Action StartRelease -SmokeSeconds 300` | Run the packaged start wrapper with bounded teardown |
| `./scripts/m8-vm.ps1 -Action WaitRelease -SmokeSeconds 300` | Retrieve clean-shutdown evidence |
| `./scripts/m8-vm.ps1 -Action ResetRun -ConfirmReset` | Explicitly discard only the mutable VM acceptance layer |

For pre-release development only, the feasibility media server can be exposed to a physical phone
on a trusted LAN:

```powershell
./scripts/media-dev.ps1 -PairingToken '<at-least-32-random-characters>' -AllowInsecureDevLan
```

Use the Windows host's LAN IP, port `8766`, and the same token in the debug Android app. This
deliberately uses cleartext signaling and is development-only. It cannot satisfy Milestone 9
physical-network acceptance, which requires WSS and real pairing. WebRTC media itself uses
DTLS-SRTP.

Release packaging requires initialized signing state plus all pinned runtimes. The Android
`VersionCode` must increase for every compatible update. Use `-GradleOffline` only when the
selected Gradle cache is already complete; `-NoArchive` is useful for a faster staged-directory
smoke but is not the final distributable.

For example:

```powershell
./scripts/initialize-release-signing.ps1
./scripts/package.ps1 -Version 0.1.4 -VersionCode 5
```

Never print, copy, commit, or package `.secrets/android-signing.properties` or the signing key.
Back up both securely together; losing the key prevents updates over an installed APK.

Install once per clone with `uv run --frozen pre-commit install --install-hooks`. Each commit checks
the staged snapshot (pre-commit temporarily hides unrelated unstaged edits). Formatting can modify
files; review and stage those corrections before retrying the commit. Ruff uses the same pinned
version as `pyproject.toml`. Hygiene checks cover JSON/YAML/TOML/XML syntax, merge markers,
case-colliding paths, private keys, oversized files, whitespace, and line endings. PowerShell files
also pass the parser.

`scripts/pre-commit-tests.ps1` combines the hook's file list with the Git index, including deleted
paths and both sides of renames. The hook runs even when no staged file still exists. It prints
the selected suites and Python test directories before running them, deduplicates overlapping
suites, and fails the commit if any check fails. Use `-ListOnly` to inspect the selection without
executing it.

| Staged change | Software checks |
| --- | --- |
| Python application/service/package source | Its component tests and all transitive Python consumer suites, plus Ruff/format and whole-host strict mypy |
| Python component tests only | The owning component suite, without unrelated consumer tests |
| Host source | Host tests and fake-lesson integration; host settings also select provider-router tests |
| Speech source | Speech, local-AI, provider-router, host, launcher, and fake-lesson tests |
| Media source/tests | Dedicated real aiortc tests and media type checks |
| Gateway security source | Security, host, launcher, fake-lesson, and media tests |
| Python wire bindings | Python consumers/schema tests and media tests |
| Android source/resources/build files | Core/app JVM tests, `lintDebug`, and `assembleDebug` in one Gradle invocation |
| Godot source/resources/project files | Headless import, C# build, renderer self-test |
| C# contract source/project files | C# tests and Godot consumer checks; C# test-only changes select C# tests |
| Lesson/environment JSON | Catalog/consumer tests; lessons also run JSON Schema checks |
| Windows wrappers, packaging scripts, release manifests | Launcher/distribution tests and applicable syntax checks |
| VM script/config/templates | Static VM fixture tests; no VM is launched |
| Shared schemas/fixtures, Python dependencies, CI workflows, hook/test infrastructure | Complete software suite; Python dependency changes also run the frozen media/speech dependency vulnerability audit |
| Markdown, project license, third-party notice text | Hygiene checks; application suites skipped |
| Unclassified code/configuration/resources | Complete software suite until an explicit mapping is added |

Selection is at the component-suite level, not a claim that each individual test depends on every
changed line. Keep the reverse dependency table in the dispatcher current when adding a component
or cross-component import; regression tests also compare it with actual Python imports, including
lazy imports. New non-imported resources need an explicit path rule. Do not use changed-file names
alone to guess which individual test functions to skip.

Selected Python suites do not apply the whole-tree 85% coverage threshold to a partial run. The
complete Python/all gates retain that threshold. Python-only commits do not require Java, Android
Studio, Godot, or model weights. Tool environments need network access on first installation;
dependency vulnerability checks also need their advisory service. Hardware, emulator interaction,
acoustic, model inference, packaging/signing, VM execution, and performance benchmarks remain
explicit commands and never run implicitly as commit hooks. CI's Android job runs the same JVM,
lint, and debug-build tasks; the Linux hygiene job skips the Windows-only hooks.

The Milestone 8 VM workflow is documented in `docs/testing/m8-clean-vm.md`. It uses a Windows
guest plus the Android Studio emulator on the host. This is clean-system software acceptance only,
not physical-phone, intended-Wi-Fi, hardware-codec, acoustic, or performance evidence.

For Android Studio emulator development, run `adb reverse tcp:8766 tcp:8766`, keep the media
server on loopback, and connect the debug app to its default `127.0.0.1:8766`. Stop the server as
soon as the audio check is finished. Emulator results complete the Milestone 1 architecture proof
but never count as Milestone 9 physical-device acceptance.

After building and launching the Godot player, replace the diagnostic source with the local
renderer bridge by adding `-Source Renderer` to `media-dev.ps1`. Keep `-BindHost 127.0.0.1` when
using `adb reverse`. This source currently requires Windows; it does not make the signaling path
release-safe. Build success alone does not prove live viewport/audio delivery.
