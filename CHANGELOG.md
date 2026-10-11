# Changelog

All notable project changes are recorded here. The project is not yet released.

## Unreleased

### Added

- Initial monorepo foundation, contracts, deterministic fake lesson host, development scripts,
  tests, architecture documents, and CI definitions.
- Native Android WebRTC receiver with video rendering, application-audio playout, runtime
  microphone permission, and hold-to-talk microphone control.
- Renderer-neutral Windows media feasibility peer with generated 1280x720 video, 48 kHz
  application audio, authenticated signaling, inbound microphone consumption, and loopback tests.
- Locked Python, Gradle-wrapper, and NuGet dependency resolution plus dependency vulnerability
  auditing.
- Android Studio emulator proof of native VP8 video, audio playout startup, reverse microphone
  frames, and reconnect through `adb reverse`, explicitly separate from physical acceptance.
- Godot 4.7.2 .NET renderer project with an animated primitive, a 1280x720 `SubViewport`, a
  two-second self-stopping application tone, shared-memory media publishers, headless validation,
  and a Windows export command.
- Closed version 1 session-control contracts with strict Python, Kotlin, and C# bindings and
  shared cross-language fixtures.
- Host-owned deterministic lesson orchestration, native Android lesson controls, and an outbound
  loopback Godot control client with cancellation, retry, timeouts, recoverable failures, and
  bounded cleanup.
- Provider-neutral local AI interfaces, llama.cpp/Qwen3 dialogue, whisper.cpp multilingual
  recognition, bilingual lesson policy, bounded session memory, and ephemeral microphone capture.
- Reproducible Qwen3 4B/1.7B model comparison and English/Bulgarian human-speech benchmark with
  pinned runtimes, weights, fixture provenance, and explicit privacy/accuracy limits.

### Changed

- Replaced the unlicensed Unity proof with the MIT-licensed Godot renderer while retaining the
  renderer-neutral aiortc and native Android boundaries.
- Completed Milestone 1 on the verified native-emulator architecture proof and moved the entire
  physical phone/Wi-Fi/target-hardware acceptance bundle to the mandatory Milestone 9 release
  gate without treating emulator evidence as hardware evidence.
- Completed Milestone 2 on unit, integration, Godot runtime, real aiortc, and API 34 emulator
  evidence.
- Completed Milestone 3 on real local dialogue/recognition, structured bilingual fixtures, failure
  handling, measured latency/memory, and host integration; natural speech remains Milestone 4.

### Fixed

- Non-trickle Android signaling now gathers ICE once instead of waiting forever under continuous
  gathering, and malformed host input fails cleanly instead of escaping from URL construction.
- Development scripts isolate Android user state under the ignored repository cache.
