# govor.ai

govor.ai is a privacy-first, local-first English teacher for a Bulgarian learner. A Windows
host performs rendering and AI work; a native Android client provides video, audio,
push-to-talk, subtitles, and simple lesson controls over the local network.

The active 3D renderer is Godot 4.7.2 .NET. It feeds a renderer-neutral local media bridge; aiortc
owns WebRTC and the native Android client owns display/audio/microphone interaction. Unity is not
part of the project stack.

The project is under active development. Milestone 0 established a reproducible monorepo,
Milestone 1 completed the native-emulator media architecture proof, Milestone 2 completed the
validated session skeleton, Milestone 3 integrated local bilingual recognition/dialogue, and
Milestone 4 completed Kokoro/Piper/eSpeak speech, accent-aware IPA, real alignment, synchronized
subtitles, speed control, and word replay. Milestone 5 adds four guided scenarios, deterministic
gentle correction and explainable difficulty adaptation, Android scenario/progress controls, and
local SQLite resume/history without retaining recordings or complete transcripts. The default
lessons now live in the JSON catalog under `assets/lesson-content`, and Android discovers the
available list from the host. Packaged Windows users can add a local JSON lesson or multi-JSON ZIP
through `Manage-Lessons.cmd`; the host validates and publishes the new catalog to connected clients
without a restart. `Create-Lesson.cmd` can generate a validated new lesson with the running local
LLM from a topic plus optional difficulty, environment, and length, then publish it through the
same live catalog path. Milestone 6
adds the animated procedural teacher, PCM/real-phoneme lip synchronization, and validated dynamic
café, supermarket, airport, and home environments. Milestone 7 adds independently selectable,
explicitly opt-in OpenAI-compatible providers while retaining a hard offline-only default and
protected Windows credentials. Physical-phone, Wi-Fi, hardware-codec, performance, and bounded
stability acceptance belongs to the final release milestone. Milestone 8 is complete: the portable
Windows package, signed Android APK, integrity-checked model setup, HTTPS/WSS pairing, stable update
identity, license/source bundle, clean-Windows QEMU/WHPX run, and host-emulator release path passed.
Milestone 9 has since passed the objective physical-phone/Wi-Fi, codec, lifecycle, performance,
bounded-stability, bilingual lesson, restart, and cleanup rows on the exact post-audit candidate.
The learner confirmed on 2026-10-22 that the moving phone scene was visible and teacher speech was
audible and intelligible, completing Milestone 9. VM/emulator evidence is not used for any physical
row.

## Quick start (Windows PowerShell)

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi
./scripts/test.ps1 -Scope all
./scripts/renderer-scene-smoke.ps1
./scripts/dev.ps1 -Mode mock
./scripts/dev.ps1 -Mode local -PairingToken '<at-least-32-random-characters>'
./scripts/progress.ps1 -Action View
./scripts/progress.ps1 -Action DeleteAll -ConfirmDelete
```

The default fake/local host, local AI services, and Godot control client bind/connect on loopback
only and never call a cloud service after the pinned artifacts are downloaded. Cloud adapters
require explicit provider selection plus `offline_only=false`; cloud recognition additionally
requires explicit microphone-upload consent. See `docs/privacy/cloud-providers.md` before opting in.
The exported renderer must exist before `dev.ps1` starts the combined development stack. See
`docs/development/setup.md` and `docs/milestones/STATUS.md` for prerequisites, verified results,
and exact resume commands.

To add or edit guided lesson content without changing Python or Android code, see
`docs/development/lesson-content.md`.

## Safety and privacy status

- Cloud providers are optional and disabled by the offline-only default; telemetry is absent.
- Provider secrets live in Windows Credential Manager, never settings, Android messages, or logs.
- Local inference services must remain loopback-only.
- Microphone recordings and learner data are ignored and must not be committed.
- Health metadata distinguishes fake and local providers. Local mode uses real offline
  recognition, dialogue, and speech; deterministic development fakes remain explicitly labeled.
- The Milestone 1 media peer is real WebRTC with generated diagnostic media, not a provider mock;
  its cleartext trusted-LAN signaling and debug APK are not production-safe.
- No hardware acceptance claim is made without a physical Android device test record.
- Renderer scene data is restricted to deterministic catalog IDs; model output cannot choose
  paths, downloads, scripts, or arbitrary resources.

The authoritative product brief is `docs/MASTER_SPEC.md`.

## Release-candidate packaging

Initialize the private signing state once, then give every Android update a higher version code:

```powershell
./scripts/initialize-release-signing.ps1
./scripts/package.ps1 -Version 0.1.4 -VersionCode 5
```

The resulting ignored artifacts are written below `.cache/dist`: a signed release APK, a portable
Windows ZIP, and a digest manifest. The Windows learner runs `Setup-Govor.cmd` once while online,
then `Start-Govor.cmd`; normal lessons remain offline. Signing keys stay in ignored `.secrets` and
must be backed up privately. See `docs/user-guide/windows.md`, `docs/user-guide/android.md`, and
ADR-0011 before distributing the candidate.

The completed clean-Windows procedure is in `docs/testing/m8-clean-vm.md`. The fixture requires a
caller-supplied Windows 11 x64 ISO plus its independently recorded SHA-256 and keeps its clean base
and mutable run layer under ignored `.cache/m8-vm`. The test image is never distributed with
govor.ai, and evidence applies only to the exact recorded image.
