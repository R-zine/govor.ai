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
local SQLite resume/history without retaining recordings or complete transcripts. Milestone 6
adds the animated procedural teacher, PCM/real-phoneme lip synchronization, and validated dynamic
café, supermarket, airport, and home environments. Milestone 7 adds independently selectable,
explicitly opt-in OpenAI-compatible providers while retaining a hard offline-only default and
protected Windows credentials. Physical-phone, Wi-Fi, hardware-codec, performance, and soak
acceptance remains mandatory in the final release milestone.

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
