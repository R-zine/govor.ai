# Milestone 8 release packaging and distribution evidence

- Date: 2026-10-14 through 2026-10-17
- Time zone: Europe/Kyiv
- Windows process build: 10.0.26200
- GPU: NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94
- Android target used: Android Studio API 34 AVD
  `Pixel_3a_API_34_extension_level_7_x86_64`, serial `emulator-5554`
- Evidence class: development Windows machine plus native emulator; not clean-Windows or physical
  target-hardware acceptance

## Implementation exercised

The release path packages an embedded CPython 3.12 environment, hash-locked Python dependencies,
exported Godot 4.7.2 player, llama.cpp b11540, whisper.cpp b5454, application/configuration source,
learner documentation, notices, and corresponding source. The launcher checks the package and
models, keeps mutable data below a protected per-user root, creates a stable TLS identity, prints
pairing details, forces local/offline providers, starts each child in a Windows Job Object, and
stops the process tree in reverse order.

The phone-facing release gateway implements one-time HTTPS pairing, certificate-fingerprint
pinning, random device credentials, authenticated WSS, pairing expiry/rate/device limits, and
bounded messages. Android encrypts the stored credential with an Android Keystore AES-GCM key.
The debug cleartext token path remains separate.

The Android release build reads the semantic version name and monotonically increasing version
code from packaging properties. The signing initializer creates one ignored RSA-3072 JKS identity
plus ignored Gradle properties and removes inherited ACL entries. Re-running the initializer
retained the identity. No password, private key, pairing code, or device credential is recorded in
this evidence.

## Commands and results

### Signing and package

```powershell
./scripts/initialize-release-signing.ps1
./scripts/initialize-release-signing.ps1
./scripts/package.ps1 -Version 0.1.1 -VersionCode 2 -NoArchive `
  -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
./scripts/package.ps1 -Version 0.1.1 -VersionCode 2 `
  -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
```

Results:

- Both signing commands passed; the second preserved the existing key. The ignored directory ACL
  granted only the interactive user and the managed execution identity used for the verification.
- Godot release export, Android release lint/build, APK signature verification, embedded Python
  dependency installation with hashes, package import smoke, and launcher doctor passed.
- The signing certificate used a 3072-bit RSA key and SHA-256 digest
  `b7022cb8bbcc0a4828cf73e5ef958e1b431ccce697020577c4a502a66ec59843`.
- `aapt` reported package `ai.govor.app`, `versionCode=2`, `versionName=0.1.1`, minimum SDK 26,
  and target SDK 34.
- The APK was 55,425,169 bytes with SHA-256
  `7e372b5b487d47e85018b55c9aceca03c7ced6c4a7822f764b0471d5270b755a`.
- The package installed 56 hash-pinned Python distributions and printed
  `GOVOR_RELEASE_IMPORTS_PASS`; `doctor` printed `Package prerequisites: ready`.
- The 0.1.1 archive-enabled rerun produced the portable directory, signed APK, artifact digest manifest,
  and Windows ZIP. `tar -tf` successfully enumerated the ZIP from its root setup/start commands
  through the bundled app/runtime content. The final ZIP was 310,891,123 bytes with SHA-256
  `a801b1b8efdccc91638f102cafd330cb533f01e927580f2de7426fe23c884a4d`. Direct archive extraction
  confirmed that its corresponding-source copy of `scripts/test.ps1` contains the corrected
  gateway-security mypy source root.

An initial sandboxed package attempt could not access `C:\Users\PC\.gradle`; the same command ran
with approved access to the existing cache. That first approved run exposed a StrictMode access to
an optional JSON property in `release-notices.json`. The script now tests the property collection
before access; the complete rerun passed. These were packaging-environment/script failures, not
successful evidence.

### Clean-system entrypoint failure and corrected candidate

On 2026-10-17, the user double-clicked `Setup-Govor.cmd` from the 0.1.1 candidate on the clean
acceptance system. The embedded launcher printed:

```text
usage: govor.ai [-h] [--install-root INSTALL_ROOT] {doctor,model-status,install-models,start} ...
govor.ai: error: the following arguments are required: command

Setup failed. No unverified model file was installed.
```

This is a verified failed acceptance attempt, not a learner error and not a passing clean-system
result. The batch files quoted `%~dp0` directly. That expansion ends in a backslash, which caused
the Windows argument parser to consume the following `doctor`, `install-models`, or `start` token
into the quoted install-root argument. The existing package smoke invoked Python directly and
therefore did not cross the faulty learner-facing boundary.

The corrected 0.1.2 candidate normalizes `%~dp0` to a full path without a trailing separator before
passing it to Python. A repository regression checks both wrappers, and packaging now invokes both
staged command files through `cmd.exe` in an internal doctor-only mode:

```powershell
./scripts/package.ps1 -Version 0.1.2 -VersionCode 3 -NoArchive `
  -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
```

That package passed Godot export, signed Android build/signature verification, dependency/source
staging, import smoke, direct doctor, and both batch-wrapper smokes. All three doctor paths printed
`Package prerequisites: ready`. The clean system must still execute the corrected normal setup,
model installation, start, pairing, lesson, and shutdown flow before Milestone 8 can complete.

The final corrected archive command also passed:

```powershell
./scripts/package.ps1 -Version 0.1.2 -VersionCode 3 `
  -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
```

- Windows ZIP: 310,894,467 bytes; SHA-256
  `816d503a6ff1467e2979220a77098f2dbe11a775a689e24b7f40778daf1e034f`.
- Signed Android APK: 55,425,169 bytes; SHA-256
  `153101ab250774249fa7048101998d2cda8ed8176a82893e083bc8d49f4fdaa5`;
  version name 0.1.2, version code 3, and the same RSA-3072 release identity.
- `tar -tf` enumerated the archive. Direct extraction of both root command files confirmed the
  normalized install-root logic is present in the emitted ZIP.

### Model integrity and distribution materials

`config/release-models.json` pins the exact URI, revision, byte size, SHA-256, destination, and
license for six required artifacts: Qwen3 4B, Whisper multilingual small, Kokoro model/voices, and
Piper Bulgarian model/config. Installer tests proved missing, short, wrong-hash, valid, and atomic
download behavior. The packaged launcher reverified the already installed files before starting.

The package included these independently hash-checked runtime notices:

| File | Bytes |
| --- | ---: |
| `GODOT-LICENSE.txt` | 1,149 |
| `GODOT-COPYRIGHT-AND-NOTICES.txt` | 100,108 |
| `LLAMA-CPP-LICENSE.txt` | 1,078 |
| `WHISPER-CPP-LICENSE.txt` | 1,078 |
| `WEBRTC-ANDROID-WRAPPER-LICENSE.txt` | 1,068 |
| `WEBRTC-AND-THIRD-PARTY-NOTICES.md` | 788,358 |

The distribution also contained Python/.NET/LLVM notices, installed Python package license files,
the shipped govor.ai source tree, and exact upstream archives for Piper (24,738,865 bytes),
Phonemizer (241,701), eSpeak NG (17,739,803), and espeakng-loader (4,595). Every upstream archive
matched `config/release-sources.json` before copying.

### Signed update and persistent credential

```powershell
adb install -r .cache/dist/govor.ai-0.1.1-android-release.apk
adb shell dumpsys package ai.govor.app
```

The installed signed release changed from version code 1/name 0.1.0 to code 2/name 0.1.1. The first
install time stayed `2026-10-14 21:59:11`; the update time became `2026-10-14 22:22:31`, proving an
update rather than an uninstall/reinstall. The progress database SHA-256 was identical before and
immediately after the update:
`4add036f08be10dfdbd652f8ef8d9044e2b01374cdcecd4d8fa031fd10578e41`.

The 0.1.1 launcher reused the existing Windows TLS certificate fingerprint. In the Android release
UI, only `10.0.2.2:8766` and `10.0.2.2:8765` were entered; the one-time code and certificate field
were left blank. Android decrypted and reused its stored device credential, and both media and
lesson channels connected over WSS. No `adb reverse` was configured.

### Complete release lesson

The packaged launcher was started with the staged 0.1.1 embedded Python, the existing verified
model directory, and isolated protected test data. The AVD was restarted with its installed
emulator's explicit `-allow-host-audio` switch. Two short supervised WAV playbacks through the PC
advanced café exercises 1 and 2; each playback stopped synchronously.

The development machine has no present recording endpoint, so the final turn used the emulator's
installed primary interface rather than making an acoustic claim. The installed
`emulator_controller.proto` documents `injectAudio` as PCM input to the virtual Android microphone.
The temporary ignored test environment used pinned `grpcio==1.75.1`, generated only message
bindings from that installed proto, and injected a mono PCM16 phrase while ADB held the signed
app's real push-to-talk control:

```powershell
C:\Users\PC\anaconda3\python.exe -m pip install --target .cache/m8-grpc grpcio==1.75.1
C:\Users\PC\anaconda3\Library\bin\protoc.exe `
  --proto_path="$env:LOCALAPPDATA\Android\Sdk\emulator\lib" `
  --proto_path='C:\Users\PC\anaconda3\Library\include' `
  --python_out='.cache\m8-grpc' emulator_controller.proto
C:\Users\PC\anaconda3\python.exe .cache\m8-grpc\inject_audio.py `
  .cache\m8-learner-4.wav
```

Whisper returned `Here, please. I will have my coffee for here, please.` The signed UI displayed
`Lesson complete · progress saved` and disconnected the lesson. The structured database view then
reported café `completed_count=1`, `exercise_index=3`, and `successful_exercises=3`; the database
was 45,056 bytes with SHA-256
`0b5523f3abb76e35db04a718689c758558f321e344719a64ee05b2967d68df84`.

An earlier emulator run omitted `-allow-host-audio`; the emulator's own help explains that it
otherwise zeroes input, so the turn correctly produced a no-speech response. Two later acoustic
turns advanced the lesson, but the third was not reliably recognized. Installing the temporary
loopback injection tool took longer than the configured learner-response deadline, producing the
expected recoverable timeout. The app's normal **Retry lesson** action resumed exercise 3, and the
promptly injected retry completed. None of these failed attempts is counted as a passing result.

### Shutdown

The launcher console was stopped with Enter, the release app was force-stopped, and the emulator
was closed immediately after the audio test. The launcher printed that managed children were
closed. A final process/listener check found zero listeners on ports 8765–8768 and zero
package-owned processes. No tone, speech, media server, or emulator audio remained active.

### Final automated gates

```powershell
./scripts/test.ps1 -Scope media
./scripts/test.ps1 -Scope all
./scripts/test.ps1 -Scope contracts
uv run --frozen --extra media --extra speech pip-audit `
  --cache-dir .cache/pip-audit-m8-entrypoint-fix
$env:PRE_COMMIT_HOME = Join-Path (Resolve-Path '.cache').Path 'pre-commit-m8-entrypoint-fix'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = 'C:/Users/PC/Documents/GitHub/govor.ai'
uv run --frozen pre-commit run --all-files
```

The first full-suite attempt exposed a stale focused-check boundary: media imported the new
gateway-security package, but its mypy command did not include that source root. The command was
fixed, after which the media scope passed strict mypy across 12 source files and 17 tests. The full
suite then passed from the beginning. After the Windows-entrypoint regression was added, the
2026-10-17 rerun passed Ruff check/format, strict mypy, 157 Python tests at 85.51%
branch coverage, 13 Kotlin tests, 8 C# tests, 17 media tests, Godot import/build/self-test, and the
Android debug build. The dedicated contract scope passed 26 tests. The locked dependency audit
reported no known vulnerabilities, and all pre-commit hooks passed. Sandbox cache/network and Git
ownership denials were rerun with repository-local caches, approved metadata access, and
command-scoped `safe.directory`; no global Git configuration was changed. Subsequent sandboxed
processes could not see hook manifests in caches populated by approved network executions, so each
affected cache was left untouched. The recorded final result is a successful one-shot execution
from the fresh `pre-commit-m8-entrypoint-fix` cache after the corrected-candidate documentation.

## Acceptance ledger

| Milestone 8 criterion | Result | Evidence/limit |
| --- | --- | --- |
| Clean Windows can install and launch using the guide | **blocked / not executed** | The first separate-system 0.1.1 attempt failed; a QEMU/WHPX clean fixture is now implemented but has no official ISO and has not booted Windows |
| Android connects without developer tools | verified passing with emulator limit | Signed release used pinned WSS and `10.0.2.2`, not `adb reverse`; ADB performed installation/automation, so this is not physical-user installation evidence |
| Complete lesson works on a release build | verified passing with emulator limit | Signed APK plus packaged local stack completed all three café exercises; final microphone input used the emulator's loopback injection API |
| Shutdown leaves no orphaned processes | verified passing | Zero package-owned processes and zero listeners on ports 8765–8768 |
| Local progress survives updates | verified passing | Signed 0.1.0-to-0.1.1 update preserved the progress DB byte-for-byte; the following release lesson was then persisted |
| Signing keys remain private | verified passing on development Windows | Ignored files, restricted ACL, stable identity, no secret in source/package/log output; off-machine backup procedure still belongs to the release operator |
| Required model downloads have integrity checks | verified passing | Exact size/SHA-256 plus atomic promotion; manifest and negative/positive tests passed |
| Internet unnecessary during normal lessons | verified passing with current-machine scope | The packaged local lesson used installed models and local providers only; first-run downloads still require internet |

At this checkpoint Milestone 8 was not complete because the clean-Windows row was mandatory, so no
milestone commit was allowed yet. That row later passed on the recorded QEMU/WHPX fixture and M8
was committed. These emulator results also left the Milestone 9 physical rows unexecuted at the
time; they later passed independently, and the product owner removed the fixed-duration soak gate.

The subsequent local-fixture design, 0.1.3 candidate, and still-blocked execution are recorded in
`docs/benchmarks/2026-10-17-m8-local-vm-fixture.md` and ADR-0012.
