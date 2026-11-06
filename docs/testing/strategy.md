# Testing strategy

Fast feedback covers pure domain transitions, schema validation, typed bindings, fake provider
behavior, and failure handling. Integration tests cross the host/control boundary. Hardware tests
are isolated and never replaced by mocks.

Milestone 0 quality gates are Ruff, Ruff format, strict mypy, pytest with 85% branch coverage for
the initial pure Python surface, Kotlin/JUnit tests, C#/xUnit tests, schema fixtures, an Android
debug build, pre-commit, and CI configuration review.

Commit checks select component suites and their consumers from the staged snapshot, including
deletions and renames. Regression tests exercise selection, transitive imports, deduplication,
Git index failures, and propagation of a failing suite. Android commits also run lint and debug
compilation in the JVM-test Gradle invocation. Shared contracts/dependencies/test infrastructure
retain the complete software gate; Python dependency changes include a vulnerability audit.
Partial Python test selections do not establish whole-tree coverage. See the maintained
[selection table](../development/commands.md). None of these hooks invokes hardware, a VM,
interactive emulator checks, real-model inference, or acoustic benchmarks.

The hosted Python and media jobs invoke the same `scripts/test.ps1` scopes as local checks. The
Python job explicitly syncs the speech extra before checking the complete host, and retains that
extra for its dependency audit; the media scope includes the gateway-security source root.
Validate CI changes in isolated environments rather than relying on a populated developer venv
or incremental type-check cache. Keep `apps/android/gradlew` executable in Git and LF-terminated
for the Ubuntu Android job.

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
decision. Later milestones add persistence, scene, privacy, and packaging suites. Milestone 9 owns
the complete physical-phone/Wi-Fi bundle: acoustic behavior, codecs, lifecycle,
latency/resources, monitor-off/unfocused behavior, security on the physical network path, and
recorded bounded stability runs. That bundle is complete; no fixed-duration lesson or soak is a
release gate.
