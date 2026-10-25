# ADR-0011: Ship a secure portable Windows bundle and signed Android APK

- Status: accepted; clean-Windows acceptance verified
- Date: 2026-10-15
- Milestone: 8

## Context

The learner must be able to run the local teaching stack without Python, Godot, Gradle, Android
Studio, or other developer tooling. The deployment still needs several large model artifacts, a
stable Android signing identity, an authenticated LAN gateway, and the notices/source required by
the bundled runtimes. Application updates must not overwrite learner progress, device credentials,
or model files.

An installer framework would add another privileged and update-sensitive dependency before the
portable layout has clean-machine evidence. The current product has one Windows user and one
trusted-LAN Android client, so a versioned portable archive is the smallest releasable shape.

## Decision

Produce two versioned artifacts with `scripts/package.ps1`:

- a Windows x64 portable archive containing an embedded CPython 3.12 runtime, hash-locked Python
  packages, the exported Godot player, llama.cpp, whisper.cpp, application source/configuration,
  user guides, license notices, and corresponding source; and
- an Android release APK signed by a stable user-controlled RSA-3072 key.

Keep mutable data outside the installation directory under `%LOCALAPPDATA%\govor.ai`. Models,
progress, logs, the TLS identity, and hashed gateway credentials therefore survive replacing one
versioned portable directory with another. `Setup-Govor.cmd` downloads only the six manifest
artifacts and accepts each file only after its exact byte length and SHA-256 digest pass.
`Start-Govor.cmd` runs the offline-only local stack and owns every child in a Windows Job Object;
normal exit terminates children and listeners.

The launcher creates a self-signed, current-user TLS identity and displays its SHA-256 fingerprint
plus a short-lived one-time pairing code. The original Milestone 8 client required manual copying;
ADR-0018 now transports the same values in a locally displayed/scanned QR by default while
retaining collapsed manual diagnostics. Android pins the certificate, exchanges the one-time code
over HTTPS for a random device credential, and encrypts that credential with an Android Keystore
AES-GCM key.
Control and signaling then use authenticated WSS; media remains DTLS-SRTP. The server stores only
PBKDF2-SHA256 salted hashes, limits failed pairing attempts, and permits at most eight devices.

Keep the existing cleartext token path only in the debug build and explicitly invoked development
server. It is not an upgrade or fallback path for the release APK.

The signing keystore and Gradle properties live in ignored `.secrets`, have inheritance removed
from their Windows ACL, and must be backed up privately. Every update increments Android
`versionCode` and retains the same signing identity. Losing the key prevents compatible APK
updates; it must never enter an archive, source bundle, log, or commit.

Bundle exact Godot, llama.cpp, whisper.cpp, WebRTC, Python, .NET, LLVM OpenMP, and installed Python
package notices. Bundle the complete corresponding source shipped for govor.ai plus checksum-
pinned upstream source archives for Piper, Phonemizer, eSpeak NG, and espeakng-loader. This is the
project's distribution implementation record, not legal advice.

## Consequences

- Normal lessons need no internet after first-run model installation.
- Updating is an extract-and-replace operation while protected per-user state stays in place.
- The portable bundle does not silently modify PATH, install a service, or require administrator
  rights, but Windows Firewall may still require the user to allow its two LAN listeners on a
  private network.
- There is no automatic updater, device revocation UI, certificate rotation UI, or public app-store
  distribution in this milestone.
- Android platform verification and sideload policy can change independently of the project;
  distribution instructions must follow the user's device/region and must not promise universal
  sideload availability.
- A signed 0.1.0-to-0.1.1 update, credential reuse, complete release lesson, progress preservation,
  and clean process teardown passed on the API 34 emulator. This is development evidence only.
- The first clean-system 0.1.1 setup attempt found that directly quoting batch `%~dp0` allowed its
  trailing backslash to consume the required launcher subcommand. Version 0.1.2 normalizes that
  root, regression-checks both wrappers, and invokes each packaged wrapper through `cmd.exe` during
  packaging. Version 0.1.3 forwards the bounded smoke argument through `Start-Govor.cmd` so the
  local QEMU/WHPX harness can exercise that exact entry point and deterministic teardown. Version
  0.1.4 adds the verified conditional Microsoft VC++ prerequisite, longer cold-model health wait,
  and fixture-only ICE/tone controls. ADR-0012 defines the clean-base/overlay fixture. The 0.1.4
  clean-VM flow passed on 2026-10-19; the separate physical phone/Wi-Fi/hardware bundle later
  passed in Milestone 9.

## Rejected

- Requiring a development Python, Godot editor, Gradle, or Android Studio at runtime.
- Bundling multi-gigabyte model weights in every application update.
- Storing API/device secrets in configuration files or the Android preferences database as
  plaintext.
- Trust-on-first-use without showing and checking the PC certificate fingerprint.
- Generating a new APK signing key or TLS identity on every version.
- Treating debug cleartext signaling, `adb reverse`, emulator media, or generated packages as
  clean-system or physical-device acceptance.
