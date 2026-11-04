# Bilingual reply validation and portrait QR scanning

Date: 2026-11-04. Machine: Windows 10.0.26200 x64 development PC. UI device: isolated
Android Studio Pixel 3a API 34 x86_64 emulator, 1080x2220, software graphics, Vulkan disabled,
no audio output. Network: loopback and `adb reverse`; no physical phone or Wi-Fi test.

## Diagnosis and changes

The learner reported that Bulgarian requests left the lesson open with an error, followed by an
invalid-event error. The Android teacher-turn validator required every pronunciation locale to
equal the overall reply locale. The real speech router intentionally retains English words and
their English IPA within Bulgarian help. Android therefore rejected a valid mixed reply before
playback, while the host was already waiting for playback completion; retrying could then be
invalid for the host's state.

The client now validates each word against the supported speech locales independently of the
overall reply locale. IPA, exact word ranges, audio bounds, and alignment references remain
validated. A shared bilingual fixture is decoded by Python, Kotlin, and C# and validated against
the existing version 1 schema. Kotlin tests also cover English-led mixed replies, both English
accents, and rejection of unsupported word locales, blank IPA, and incorrect ranges.

Separately, ZXing's merged activity manifest had `screenOrientation=sensorLandscape`.
`setOrientationLocked(false)` does not remove that activity setting. The application now overrides
the scanner to portrait and explicitly keeps it unexported, retaining the library theme/camera.

No host provider, model, speech routing, or versioned message shape changed. Historical milestone
acceptance and the installed 0.1.23 release are unchanged.

## Executed checks

From the repository root, initialize tool paths with `. ./scripts/common.ps1` and
`Initialize-GovorEnvironment`; Gradle additionally uses `$env:JAVA_HOME = Get-GovorJavaHome`.

- `uv run --frozen --extra speech python .cache/bulgarian-help-repro.py`: real Kokoro/Piper
  synthesis of the four bundled initial exercise help replies, no fallback. Cafe, supermarket,
  airport, and home audio durations were 12,169,541 / 12,725,625 / 11,879,000 / 13,093,500 us;
  wall times were 16.169 / 11.400 / 1.577 / 1.695 seconds. This bounded script stores only
  metadata in `.cache/bulgarian-help-repro.json`; nothing was played.
- `uv run --frozen --extra speech python .cache/bulgarian-pipeline-repro.py`: synthetic Bulgarian
  learner speech through real Whisper small, Qwen3 4B, the teaching engine, Kokoro/Piper, Python
  wire validation, and renderer-animation construction. Two consecutive help replies passed
  within the unchanged 30-second processing bound: 22.357 and 20.031 seconds. Their audio
  durations were 12,396,916 and 12,413,375 us. Stage times and results are in
  `.cache/bulgarian-pipeline-repro.log`; the owned model server was stopped in `finally`.
- `./apps/android/gradlew.bat -p apps/android :core:test --tests ai.govor.core.ContractsTest
  --no-daemon --no-parallel --no-configuration-cache`: the new bilingual regression **failed**
  against the old validator, then passed after the correction. The pre-fix log is
  `.cache/bulgarian-qr-before-fix.log`.
- `./apps/android/gradlew.bat -p apps/android :core:test :app:testDebugUnitTest :app:assembleRelease
  --no-daemon --no-parallel --no-configuration-cache`: passed, including QR decoding and release
  vital lint. Both debug and release merged manifests declare the internal scanner as portrait.
  Log: `.cache/bulgarian-qr-after-fix.log`.
- A task-only copy of the unsigned release APK was signed with the development key and installed
  **only in the isolated emulator**. `uv run --frozen python .cache/bulgarian-qr-ui.py` opened the
  actual release UI scanner twice, waited for camera instructions, asserted the resumed scanner
  activity and 1080x2220 display, captured the preview, and cancelled back to pairing each time.
  Result and screenshots: `.cache/bulgarian-qr-ui/scanner-result.json`,
  `scanner-portrait-0.png`, `scanner-portrait-1.png`, and `pairing-after-cancel.png`.
- `uv run --frozen --extra speech pytest tests/contracts -q`: **55 passed**.
- `./scripts/test.ps1 -Scope csharp`: **13 passed**.
- `uv run --frozen --extra media --extra speech pip-audit --cache-dir
  .cache/pip-audit-bilingual-regression`: **exit 0, no known vulnerabilities**.
- `./apps/android/gradlew.bat -p apps/android :app:assembleDebug --no-daemon --no-parallel
  --no-configuration-cache`, then `uv run --frozen --extra media --extra speech python
  .cache/bulgarian-playback-ui.py`: the corrected native UI fixture **passed** real mixed
  Bulgarian help playback, exercise retention, English return/advancement, and leave/zero-session
  cleanup. Recognition and dialogue were explicitly scripted in this UI fixture; synthesized
  speech, wire decoding/validation, AudioTrack playback, and native state transitions were real.
  The opening turn and both replies logged normal completion without a client error. Artifacts:
  `.cache/bulgarian-playback-ui.log`, `.cache/bulgarian-qr-ui/bilingual-result.json`,
  `bilingual-android.log`, `bulgarian-help-played.png`, and `english-return-played.png`.

- `./scripts/test.ps1 -Scope all`: **exit 0**; 356 Python tests at 85.63% branch coverage, Kotlin
  core/app tests, 13 C# tests, 21 real aiortc media tests, Godot import/build/headless self-test,
  and debug APK assembly. Ruff/format and strict mypy passed. Log:
  `.cache/bulgarian-qr-full-tests.log`. Existing Starlette deprecation and ignored pytest-cache
  access warnings did not fail the suite.
- The focused `git commit -m "fix: accept bilingual replies and keep QR scanning portrait"`
  runs the installed formatting/quality, JSON contract, and affected-application hooks. Shared
  fixtures select the complete `all` scope. Commit output: `.cache/bulgarian-qr-commit.log`.

Artifact completion timestamps (UTC, 2026-11-04): bundled speech 13:52:34, real-provider pipeline
13:55:50, portrait scanner 14:04:39, audit 14:06:48, native lesson/cleanup 14:10:03, and full
software gate 14:12:18. All model/media test services and the owned emulator have been stopped;
ports 8765-8768 have no listener and no audio remains.

## Failed harness attempts and limits

The first scanner screenshot was taken as the activity resumed, before the camera preview was
drawn. Its accessibility tree was already the scanner, but its PNG still showed pairing. The
repeated check waited for the scanner instructions and rendered preview; only those corrected
captures count as preview evidence.

An initial audit wrapper treated pip-audit's success text on stderr as a PowerShell error. The
corrected wrapper captured the actual exit code 0. A first native bilingual fixture run reached
the opening real English turn but ended with a provider error; it is not counted as a pass.
The later run with explicit test-only exception diagnostics passed under the same 30-second
provider bound; the initial generic provider failure has no retained exception cause and is not
attributed to the Android locale validator.

Synthetic learner audio is not physical microphone evidence. Emulator playback cannot establish
human intelligibility, camera decoding on the real phone, acoustics, Wi-Fi, hardware codecs, or
new release acceptance. Private lessons/progress and the physical phone installation were not
modified by these isolated checks.
