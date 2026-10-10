# Troubleshooting

- **Git says dubious ownership:** use the command-scoped `safe.directory` command in `AGENTS.md`.
- **Java is not found:** install Android Studio or set `JAVA_HOME` to JDK 17.
- **Android SDK is not found:** set `ANDROID_SDK_ROOT` or install it under
  `%LOCALAPPDATA%\Android\Sdk` with Platform/Build Tools 34.
- **Gradle or .NET is absent:** rerun `./scripts/bootstrap.ps1`; repository-local copies are used.
- **ADB daemon cannot start:** verify no conflicting ADB process/firewall policy and retry outside
  a restricted sandbox. Do not count emulator/failed enumeration as physical-device evidence.
- **Production mode refuses to start:** expected until real providers and security controls exist.
- **LAN bind is rejected:** expected until pairing, authentication, and TLS are implemented.
