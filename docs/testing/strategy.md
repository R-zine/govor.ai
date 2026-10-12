# Testing strategy

Fast feedback covers pure domain transitions, schema validation, typed bindings, fake provider
behavior, and failure handling. Integration tests cross the host/control boundary. Hardware tests
are isolated and never replaced by mocks.

Milestone 0 quality gates are Ruff, Ruff format, strict mypy, pytest with 85% branch coverage for
the initial pure Python surface, Kotlin/JUnit tests, C#/xUnit tests, schema fixtures, an Android
debug build, pre-commit, and CI configuration review.

The deterministic fake lesson proves orchestration without models or credentials. Its generated
tone and Android playback-completion event prove the bounded fake playback code path on the
emulator; they do not prove speech quality, physical acoustics, production speech routing,
hardware codecs, or physical Android compatibility.

The Milestone 1 media tests are not mocks: two actual aiortc peer connections negotiate generated
live video and application audio plus a reverse audio track. They prove signaling/track semantics
on one Windows process. They do not prove Kotlin/libwebrtc interoperability, physical speaker or
microphone behavior, LAN behavior, hardware codecs, Godot viewport capture, or user-visible latency.

Milestone 1 adds signaling, the real WebRTC peer, native-emulator video/audio/microphone,
reconnect, cleanup, and renderer-bridge tests. Milestone 2 adds shared cross-language fixtures,
complete host/Android/Godot turn-cycle tests, invalid/out-of-order message rejection, injected
failure, timeout, cancellation, correlation/log-redaction, and repeated-session teardown tests.
Milestone 4 adds real English/Bulgarian/fallback audio generation, curated accent-aware IPA,
model-alignment/null-fallback checks, speed-duration ordering, deterministic fallback, native
emulator `AudioTrack`/highlight/replay/word-selection evidence, and a separate human listening
decision. Later milestones add persistence, scene, privacy, and packaging suites. Milestone 9 owns the complete
physical-phone/Wi-Fi bundle: acoustic behavior, codecs, lifecycle, latency/resources,
monitor-off/unfocused behavior, security on the physical network path, and the 30-minute soak.
