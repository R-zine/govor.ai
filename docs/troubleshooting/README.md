# Troubleshooting

## Release package

- **`Setup-Govor.cmd` reports that the package is incomplete:** extract the entire ZIP again into
  one directory. Do not copy only the two command files.
- **`govor.ai: error: the following arguments are required: command`:** discard the obsolete
  0.1.1 candidate, extract 0.1.2 or later into a new directory, and run its `Setup-Govor.cmd`.
  Version 0.1.1 quoted a trailing-backslash batch path incorrectly and cannot complete setup.
- **A model is missing, has the wrong size, or fails SHA-256:** restore internet access and rerun
  setup. Delete only the named invalid model if a repeated attempt cannot replace it. Never bypass
  the manifest check.
- **`llama-server` cannot start or setup reports a missing runtime DLL:** rerun `Setup-Govor.cmd`
  online and accept its Windows administrator prompt. The setup downloads the pinned Microsoft
  Visual C++ x64 redistributable directly from Microsoft and rejects a wrong size, SHA-256, or
  Authenticode signer. Do not copy arbitrary DLLs from another PC.
- **Windows SmartScreen or antivirus warns about the portable bundle:** verify the artifact digest
  against the release manifest and obtain the package through the trusted project channel. Do not
  add a blanket security exclusion.
- **Port 8765, 8766, or 8767 is already in use:** stop another govor.ai launcher or the conflicting
  process, then retry. Do not run two launchers against the same data directory.
- **The phone cannot reach the PC:** use the PC's private IPv4 address, confirm both devices are on
  the same non-isolated network, allow the packaged runtime on private Windows Firewall networks,
  and verify ports 8765/8766 were not opened to public networks or the internet.
- **QR will not scan:** clean the phone camera, raise the host display brightness, keep the entire
  square in frame, and confirm the code is no older than ten minutes. If needed, expand
  **Pair manually** and use the values in the host console.
- **Pairing is rejected:** restart the host for a fresh QR/code, confirm the phone clock is
  reasonably correct, and check that both devices are on the trusted private LAN. A successful
  code cannot be reused. Manual diagnostics still require the complete 64-character certificate
  fingerprint and both host/port values.
- **Certificate fingerprint mismatch:** stop. Confirm the fingerprint directly in the Windows
  launcher. If `%LOCALAPPDATA%\govor.ai\security` was intentionally reset, clear Android app
  storage and pair again; otherwise investigate a changed or unexpected host.
- **A previously paired phone cannot reconnect:** tap **Reconnect to saved host**. If the PC
  address changed, use **Scan a different host QR**; if the PC security directory changed, reset
  Android app storage and pair anew.
- **Models are ready but normal lessons try to use the internet:** the release launcher forces
  local providers and `offline_only=true`. Stop the app and inspect the packaged logs; do not add
  cloud credentials as a workaround.
- **Launcher shutdown appears stuck:** wait five seconds for graceful child termination. If a port
  remains open, record the process/listener details as a defect; do not start a second copy.
- **APK update is rejected:** confirm the new APK has a higher version code and the same release
  signing key. Do not uninstall first unless losing the stored device credential is acceptable.
- **No speech is captured:** grant microphone permission in Android Settings, hold the button for
  the whole response, and avoid starting while the teacher is speaking or the app is processing.

## Development checkout

- **Git says dubious ownership:** use the command-scoped `safe.directory` command in `AGENTS.md`.
- **Java is not found:** install Android Studio or set `JAVA_HOME` to JDK 17.
- **Android SDK is not found:** set `ANDROID_SDK_ROOT` or install it under
  `%LOCALAPPDATA%\Android\Sdk` with Platform/Build Tools 34.
- **Gradle or .NET is absent:** rerun `./scripts/bootstrap.ps1`; repository-local copies are used.
- **ADB daemon cannot start:** verify no conflicting ADB process/firewall policy and retry outside
  a restricted sandbox. Do not count emulator/failed enumeration as physical-device evidence.
- **Debug LAN bind is rejected:** use the explicit insecure development command only on a trusted
  test network. Release packaging has a separate authenticated TLS path.
- **Emulator microphone contains silence:** recent emulator builds require `-allow-host-audio` for
  a host capture device; deterministic automation may use the emulator's loopback `injectAudio`
  API. Neither is physical-phone or acoustic evidence.
