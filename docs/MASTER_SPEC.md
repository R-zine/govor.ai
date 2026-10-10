# govor.ai — Master Codex Implementation Prompt

## 0. Your role and overall instructions

You are the lead architect, senior engineer, QA engineer, and implementation agent for **govor.ai**, a privacy-first, local-first, AI-powered English learning application for a native Bulgarian speaker.

Your task is to **design, scaffold, implement, test, benchmark, package, and document a complete working application**, not merely produce a prototype or architectural proposal.

You have permission to make reasonable engineering decisions, install development dependencies, create files, implement features, execute tests, benchmark hardware, refactor code, and maintain the repository.

Work autonomously wherever possible. Do not repeatedly ask for decisions that can be resolved through reasonable engineering judgment, research, or experimentation.

However:

- Do not claim something works without verification.
- Do not silently substitute mocked behavior for real functionality.
- Do not manufacture test results, benchmarks, screenshots, or implementation evidence.
- Do not label a milestone complete if its acceptance criteria have not been satisfied.
- Do not introduce paid services or transmit personal data externally by default.
- Do not commit credentials, model weights, signing keys, generated recordings, or private learning data.
- Do not prioritize completing checklists over building a genuinely usable application.

If an architectural decision is uncertain, implement a small experiment and make the decision using measured evidence.

**The ultimate goal is a dependable application that a nontechnical older adult can launch on her Android phone and use independently.**

---

## 1. Product vision

govor.ai is an immersive English learning application focused on two abilities:

1. Understanding spoken English.
2. Becoming comfortable speaking English in realistic everyday situations.

The primary learner is an adult native Bulgarian speaker with some basic English knowledge who struggles with conversational comprehension, spontaneous speaking, and pronunciation.

The application must accommodate those difficulties without feeling childish, judgmental, or complicated.

### Core experience

The application runs primarily on a Windows PC containing an NVIDIA RTX 3060 or similar GPU.

The learner uses a native Android application on a phone connected to the same Wi-Fi network.

The Windows PC performs:

- AI text generation and reasoning.
- Speech recognition.
- Text-to-speech synthesis.
- Speech phonemization and alignment.
- Teaching and lesson orchestration.
- 3D environment rendering.
- Avatar animation.
- Video/audio encoding.
- Storage of learning progress.

The Android device performs:

- Displaying the streamed 3D environment.
- Playing teacher audio.
- Capturing microphone input.
- Rendering interactive subtitles and pronunciation information.
- Displaying simple, accessible controls.
- Managing session connectivity.

The Android device must not require local AI inference or 3D rendering.

The learner should be able to sit comfortably anywhere within Wi-Fi range, open the Android app, and have an interactive lesson without using the PC monitor, microphone, or speakers.

### Local-first principles

The application must work without an internet connection after installation and initial model downloads, provided the PC and Android device can communicate over the local network.

All AI processing should run locally by default.

Paid cloud APIs must be optional, independently configurable, and disabled by default.

No account registration, subscription, telemetry, analytics platform, or third-party cloud backend should be required.

---

## 2. Primary functional requirements

### 2.1 Bilingual conversation

The learner must be able to speak naturally in English or Bulgarian.

Examples of Bulgarian requests include:

- "Не разбирам."
- "Какво означава тази дума?"
- "Може ли да повториш?"
- "Кажи го по-бавно."
- "Как се произнася това?"
- "Как да кажа това на английски?"

The system must distinguish between:

- An English attempt to answer an exercise.
- A Bulgarian request for help.
- A Bulgarian attempt to express something the learner cannot yet express in English.
- A request to repeat.
- A request to slow down.
- A request for translation.
- A request for pronunciation guidance.
- An ambiguous utterance requiring clarification.

The system must not interpret every Bulgarian response as a failure.

If the learner requests help in Bulgarian, the teacher should assist and naturally return to English when appropriate.

For example:

Teacher: "What would you like to order?"

Learner: "Какво значи order?"

Teacher: "Order означава да поръчаш нещо. Например кафе или чай."

Teacher: "Would you like coffee or tea?"

The teaching logic must decide when to use English, Bulgarian, or a combination.

English remains the default instructional language, but Bulgarian provides a supportive fallback.

### 2.2 Voice-first interaction

The first version must use push-to-talk.

The teacher finishes speaking before microphone recording begins.

The learner presses and holds a large microphone button to speak, then releases it to submit the utterance.

Interruptions, barge-in, simultaneous speech, and advanced echo cancellation are not required for the first version.

Use a clear session state machine so interruption handling can be added later without redesigning the entire architecture.

### 2.3 Speech comprehension

Support:

- Natural-speed listening.
- Slower listening.
- Repetition.
- Interactive English subtitles.
- Optional Bulgarian translations.
- Word-level explanations.
- Pronunciation demonstrations.
- Accent selection between British and American English.

The learner should not need to navigate several menus to access help.

Prefer conversational help requests and simple contextual controls.

### 2.4 Phoneme-aware teaching

Phonemes are a core feature.

The app should:

- Generate accent-aware IPA transcriptions.
- Associate phonemes with words.
- Identify syllable and word stress when reliable.
- Allow the learner to inspect individual words.
- Replay individual words.
- Explain difficult sounds.
- Teach common pronunciation contrasts.
- Highlight words during spoken playback.
- Support phoneme timing where reliable alignment is available.
- Provide viseme information for avatar lip synchronization.

Differentiate between:

1. Orthographic text.
2. Phonemic transcription.
3. Phonetic realization.
4. Word timing.
5. Phoneme timing.
6. Viseme animation data.

Do not treat these as interchangeable.

Do not fabricate phoneme timestamps.

If only word-level alignment is available, the app should gracefully use word-level highlighting.

If alignment fails, audio playback must still work.

Do not use ordinary speech-to-text transcription as an authoritative pronunciation-scoring mechanism.

### 2.5 AI teacher

The teacher should:

- Maintain conversational context.
- Adjust difficulty based on demonstrated understanding.
- Use realistic everyday scenarios.
- Correct mistakes gently.
- Explain unfamiliar vocabulary.
- Encourage English responses without penalizing requests for Bulgarian assistance.
- Prefer concise, understandable explanations.
- Recognize repeated comprehension difficulties.
- Avoid overwhelming the learner with too many corrections at once.

Lessons should support both guided exercises and relatively open conversation.

Do not allow the LLM to directly control application state through unvalidated freeform text.

### 2.6 Immersive 3D environments

The teacher should appear as a 3D avatar in an appropriate environment.

Initial scenes should include:

- Café.
- Supermarket.
- Airport.
- Home or living room.

The architecture should support later additions such as restaurants, hotels, train stations, medical appointments, workplaces, and city streets.

Scenes should be dynamically assembled based on lesson context.

For example, a café scene could contain a counter, cups, tables, chairs, and a teacher positioned behind the counter.

Do not attempt to generate arbitrary high-quality 3D meshes with an LLM on every lesson turn.

Instead, use a validated scene-description contract and an extensible asset library.

The scene-generation system may decide:

- Environment template.
- Objects to instantiate.
- Object placement.
- Lighting preset.
- Camera composition.
- Character placement.
- Character gestures.
- Contextual interaction targets.

All scene descriptions must be validated against known assets and allowed parameter ranges.

Runtime scenes should be assembled and kept in PC memory. Persist source assets, configuration, and optional deterministic scene recipes on disk, but do not require exporting generated scenes to standalone 3D files.

### 2.7 Android interface

The Android app must be native Kotlin using Jetpack Compose.

Use the phone's native video decoding and audio playback facilities wherever practical.

UI requirements:

- Full-screen streamed 3D scene.
- One prominent push-to-talk button.
- A small replay control.
- Clear, readable subtitles.
- Interactive word selection.
- On-demand IPA and Bulgarian explanations.
- Simple connection-status indicator.
- Minimal settings.
- Large touch targets.
- Adjustable text size.
- Accessible contrast.

Avoid clutter.

The phone should feel like the learning experience itself, not a remote-control dashboard.

### 2.8 Progress tracking

Track learning progress locally in SQLite.

Useful information includes:

- Lesson completion.
- Conversation scenarios practiced.
- Vocabulary encountered.
- Words requested for explanation.
- Repeated comprehension difficulties.
- Exercises attempted.
- Topics practiced.
- Approximate proficiency and lesson difficulty.
- Learner preferences.

Do not save microphone recordings by default.

Provide controls to view, export, and delete learning history.

Do not store indefinite raw conversation transcripts unless explicitly enabled.

---

## 3. Proposed technology stack

Use the following default architecture, unless an early feasibility investigation demonstrates a materially better alternative.

| Subsystem                     | Preferred technology                                 |
| ----------------------------- | ---------------------------------------------------- |
| Android application           | Kotlin, Jetpack Compose                              |
| Android architecture          | MVVM, Coroutines, StateFlow                          |
| 3D rendering                  | Godot 4.7.2 .NET, C#                                 |
| Desktop orchestration         | Python 3.12+, FastAPI, asyncio                       |
| Video/audio transport         | WebRTC                                               |
| Signaling and control         | Authenticated WebSocket API                          |
| LLM inference                 | llama.cpp                                            |
| Default text model            | Quantized Qwen3 4B-class instruct model              |
| Speech recognition            | whisper.cpp, multilingual model                      |
| Natural English TTS           | Kokoro                                               |
| Bulgarian TTS                 | Piper-compatible Bulgarian voice                     |
| Deterministic speech fallback | eSpeak NG or an equivalently reliable offline engine |
| Phonemization                 | eSpeak NG / Phonemizer                               |
| Speech alignment              | Benchmark suitable forced-alignment implementations  |
| Local database                | SQLite                                               |
| Inter-module contracts        | JSON Schema, generated/validated language bindings   |
| Python dependency management  | uv                                                   |
| Android builds                | Gradle                                               |
| Windows automation            | PowerShell                                           |
| Continuous integration        | GitHub Actions                                       |

### Important implementation constraints

**Godot and the renderer-neutral aiortc bridge are the selected development architecture based on
the Milestone 1 native-emulator proof. Final physical-device, Wi-Fi, codec, performance, and soak
acceptance is deferred as one bundle to Milestone 9.**

Use a dedicated 1280x720 Godot `SubViewport` and application-owned PCM as renderer outputs.

Keep WebRTC outside the renderer: the renderer publishes only process-local frames and PCM to the
renderer-neutral aiortc gateway.

Evaluate viewport readback cadence, native video/audio tracks, signaling compatibility, Android
decoding, application-owned audio, and hardware encoding.

If synchronous Godot viewport readback proves unsuitable, investigate a Godot GDExtension,
Stride, or a dedicated native capture/hardware-encoding bridge without changing the Android wire
contract.

If a different renderer becomes necessary, record an architecture decision explaining why.

Prefer the smallest reliable solution over unnecessary framework complexity.

### GPU considerations

Do not assume all models can remain resident in VRAM simultaneously.

The RTX 3060 may have different VRAM configurations.

Detect:

- GPU model.
- Available VRAM.
- CUDA support.
- CPU capabilities.
- Available system RAM.
- Hardware video encoder support.

Benchmark model combinations under actual rendering and streaming load.

Use CPU execution for lightweight workloads when it provides better overall performance.

Provide model profiles for lower-memory and higher-memory systems.

---

## 4. Modular architecture

Create a modular monorepo with explicit boundaries.

Suggested structure:

    govor.ai/
      AGENTS.md
      README.md
      CONTRIBUTING.md
      CHANGELOG.md
      .editorconfig
      .gitignore
      .pre-commit-config.yaml

      apps/
        android/
        renderer/
        host/

      packages/
        contracts/
        domain/
        provider-interfaces/
        lesson-engine/
        dialogue-engine/
        scene-planner/
        phonetics/
        progress/

      services/
        local-llm/
        speech-recognition/
        speech-synthesis/
        alignment/
        media/
        provider-router/

      assets/
        avatars/
        environments/
        animations/
        lesson-content/

      tests/
        fixtures/
        integration/
        end-to-end/
        performance/
        security/

      scripts/
        bootstrap.ps1
        dev.ps1
        test.ps1
        build.ps1
        package.ps1
        benchmark.ps1

      docs/
        architecture/
        decisions/
        contracts/
        development/
        testing/
        benchmarks/
        milestones/
        user-guide/
        troubleshooting/

      .github/
        workflows/

Adjust package placement as necessary to avoid artificial dependencies or excessive fragmentation.

### Architectural rules

1. Every subsystem must expose an explicit, documented interface.
2. Dependencies flow toward domain contracts and interfaces.
3. Domain logic must not depend directly on Godot, FastAPI, Android, llama.cpp, or specific TTS engines.
4. Provider adapters implement interfaces defined elsewhere.
5. Rendering must not contain lesson-planning logic.
6. Android must not contain AI inference or teaching logic.
7. Models must be replaceable through configuration.
8. Serialization must use validated, versioned contracts.
9. No LLM-generated output may execute arbitrary code.
10. No major subsystem should require knowledge of another subsystem's internal implementation.
11. Keep network protocols and domain contracts separately versioned.
12. Avoid circular dependencies.
13. Prefer dependency injection and explicit configuration.
14. Keep components independently testable with fake providers.
15. Favor maintainability and readability over clever abstractions.

Different programming languages are acceptable where technically justified.

Do not introduce additional languages without a meaningful architectural benefit.

---

## 5. Required contracts

Design explicit schemas for at least the following types:

- SessionConfiguration
- SessionState
- SessionEvent
- RecognizedUtterance
- ClassifiedLearnerIntent
- DialogueContext
- TeacherResponse
- LessonDefinition
- LessonProgress
- SpeechSynthesisRequest
- SynthesizedAudio
- AlignedSpeech
- WordAlignment
- PhonemeAlignment
- VisemeTimeline
- SceneSpecification
- SceneObject
- AvatarAction
- ProviderCapabilities
- ProviderHealth
- ProviderError
- PlaybackState
- ConnectionState
- PerformanceMetrics

All cross-process messages must have:

- Schema or protocol version.
- Correlation identifier.
- Explicit message type.
- Validated payload.
- Documented error behavior.

Messages involving speech should also carry relevant language/locale, audio format, sample rate, timing reference, and utterance identifiers.

Use a canonical time base for audio, captions, and animation synchronization.

### Provider interfaces

Define interfaces conceptually equivalent to:

- TextGenerator
- SpeechRecognizer
- SpeechSynthesizer
- Phonemizer
- SpeechAligner
- DialoguePolicy
- LessonPlanner
- ScenePlanner
- RendererController
- ProgressRepository
- MediaTransport

Support capability discovery and explicit unsupported-feature errors.

For example, some speech synthesizers may provide word timestamps while others do not.

A consumer must not assume every provider supports the same metadata.

Generate Kotlin and C# contract bindings where practical, and use validated Python models.

Include positive and negative contract fixtures and compatibility tests.

Do not silently change schemas in incompatible ways.

---

## 6. Conversation and session state machine

Implement an explicit state machine.

Required states include:

- Disconnected
- Discovering
- Pairing
- Connecting
- Ready
- TeacherSpeaking
- AwaitingLearner
- Recording
- Processing
- Reconnecting
- RecoverableError
- FatalError
- Ending

For the first iteration:

1. Teacher generates response.
2. Speech is synthesized.
3. Speech plays with avatar animation.
4. Teacher playback completes.
5. Learner may begin push-to-talk.
6. Learner records speech.
7. Recording is submitted.
8. Speech is recognized.
9. Intent and language are interpreted.
10. Dialogue engine determines the next action.
11. Teacher responds.
12. Cycle repeats.

Prevent conflicting actions through state validation.

For example, reject overlapping microphone submissions during the Processing state rather than creating duplicate dialogue turns.

Include timeouts, cancellations, reconnection handling, and idempotency where relevant.

Use deterministic state-machine tests.

---

## 7. Local AI requirements

### Language model

Begin by evaluating a quantized Qwen3 4B-class instruct model with llama.cpp.

Do not assume it is automatically the best option.

Benchmark candidates for:

- English quality.
- Bulgarian quality.
- Mixed-language conversations.
- Structured-output reliability.
- Latency.
- Memory usage.
- Conversation coherence.
- Pedagogical appropriateness.

Select the default model using evidence.

The default model should be small enough to coexist with the renderer and video encoder on the target GPU.

Provide configurable context limits and conversation-history compression.

Support provider-level timeouts and retries.

Use constrained structured generation where supported.

If the LLM becomes unavailable, support a deterministic scripted lesson mode rather than allowing the whole application to become unusable.

### Speech recognition

Start with a multilingual Whisper implementation.

Test recognition for:

- Bulgarian.
- English.
- Bulgarian-accented English.
- Short utterances.
- Hesitant speech.
- Mixed-language utterances.
- Requests containing English words inside Bulgarian sentences.

Use real audio fixtures when legally and practically available.

Never assume language detection is infallible.

When confidence is insufficient, ask the learner to repeat or clarify.

### Speech synthesis

Provide:

- A natural English voice.
- Bulgarian speech synthesis.
- Voice speed adjustment.
- Replay.
- Provider-level fallback.
- Defined audio format and sample rate.
- Explicit error handling.

Keep the natural TTS provider independent of the deterministic fallback.

When the preferred synthesizer fails, the application should continue using an available offline voice.

Changing providers must not require modifying dialogue or rendering code.

### Speech alignment and phonemes

Generate pronunciation information using accent-aware phonemization.

Use speech alignment only when available and reliable.

Represent unavailable timestamps explicitly instead of guessing.

Audio metadata should be sufficient to synchronize:

- Spoken audio.
- Word highlighting.
- Optional phoneme highlighting.
- Avatar mouth movement.

When changing playback speed, keep subtitle timing aligned with the actual playback timeline.

---

## 8. Native Android requirements

Use Kotlin and Jetpack Compose.

Do not introduce React, React Native, WebView-based rendering, or PWA infrastructure for the main application.

The Android client should include:

- Hardware-accelerated video decoding when available.
- Teacher audio playback.
- Microphone recording.
- WebRTC session management.
- Secure control messages.
- PC discovery over the local network.
- Manual host address fallback.
- Pairing and reconnect functionality.
- Interactive subtitles.
- IPA display.
- Basic settings.
- Accessibility support.

### Pairing

Implement a simple first-run pairing flow.

The PC may display a pairing code or QR code.

The Android app should remember an authorized PC using secure device storage.

Prefer automatic local service discovery where supported.

Do not assume multicast discovery always works.

Provide a manual IP or hostname option.

Do not expose the app to the public internet.

### Android build and distribution

Produce:

- A debug APK.
- An installable release APK.
- Repeatable Gradle build instructions.
- APK signing instructions.
- Documentation for installing updates.

The release APK must be signed with a stable user-controlled key.

Never commit the private signing key.

Preserve app data across updates using the same application identifier and signing key.

Investigate applicable Android developer-verification requirements, including limited distribution and unverified-app installation flows.

No root access or Play Store publication should be a project prerequisite.

---

## 9. Video, audio, and network requirements

The PC renders the complete 3D environment.

The Android phone receives the rendered video and accompanying teacher audio.

Use WebRTC for low-latency audiovisual transport.

For microphone input, choose the simplest reliable transport that satisfies push-to-talk. A bounded authenticated WebSocket audio-upload protocol is acceptable initially; bidirectional WebRTC audio can be implemented if it is demonstrably simpler and more reliable.

Make the microphone transport replaceable.

Start with:

- 1280 × 720 video.
- 30 FPS target.
- H.264 hardware encoding when supported.
- Opus teacher audio where supported.
- Adjustable bitrate.
- Adaptive resolution or quality settings.
- One PC and one Android client per lesson.

Do not assume the existence of a working display, active monitor, or PC speakers is necessary.

Test rendering with the monitor off, the Godot renderer window unfocused, and the PC idle but awake.

Ensure the application does not depend on the PC's physical audio output device to stream synthesized speech.

### Network requirements

- Communication remains on the LAN by default.
- The mobile-facing gateway requires pairing and authentication.
- Local model inference services bind to loopback.
- Encrypt application traffic appropriately.
- WebRTC must use secure transport.
- Do not disable TLS certificate verification as a permanent workaround.
- Allow reconnection without restarting the lesson.
- Handle loss of Wi-Fi gracefully.
- Document necessary Windows Firewall configuration.
- Do not assume internet access is available.

Benchmark latency and packet loss under realistic Wi-Fi conditions.

---

## 10. Development workflow

The project must be easy to develop without repackaging every component after a change.

Required PowerShell commands:

- `scripts/bootstrap.ps1` — install or validate dependencies and initialize the development environment.
- `scripts/dev.ps1` — run the full development system.
- `scripts/test.ps1` — run tests with selectable levels or scopes.
- `scripts/build.ps1` — build changed or requested modules.
- `scripts/package.ps1` — create distributable artifacts.
- `scripts/benchmark.ps1` — execute performance benchmarks.

Support running the system with fake providers and without downloading large AI models.

The mocked development mode should run a realistic end-to-end lesson using deterministic text, prerecorded or generated test audio, and a simple renderer.

Where technically possible, use an already-built Godot renderer executable during development.

A change to Python lesson logic must not require rebuilding the Godot renderer.

A change to Android UI must not require repackaging the Windows backend.

A change to a provider adapter must not require building unrelated modules.

Restarting applications or processes after changes is acceptable.

Automatic hot reloading is optional.

Use lockfiles and pinned toolchain versions.

Document all external SDK prerequisites.

---

## 11. Testing and quality standards

Testing is mandatory throughout development.

Do not postpone testing until the end.

### Python

Use:

- pytest.
- Ruff.
- A static type checker.
- Coverage reporting.
- Dependency and security checks.

### Kotlin

Use:

- JUnit.
- Kotlin linting.
- Static analysis.
- Coroutine tests.
- Compose UI tests.
- Android instrumentation tests.

### C#

Use:

- NUnit or equivalent.
- Godot headless project import/build and renderer self-tests.
- .NET tests for pure C# modules outside Godot where practical.
- Static analysis and formatting.

### Pre-commit hooks

Implement hooks for:

- Formatting.
- Linting.
- Type checking where practical.
- JSON and YAML validation.
- Contract validation.
- Secret detection.
- Whitespace and line-ending checks.
- Documentation consistency.
- Relevant fast unit tests.

Keep normal pre-commit execution reasonably fast.

Reserve slow integration and GPU tests for appropriate pipelines.

### CI pipelines

Create automated workflows for:

- Python tests.
- Kotlin builds and unit tests.
- Contract compatibility.
- Pure C# tests.
- Security checks.
- Build artifact validation.

Use Windows CI runners where appropriate.

Do not require proprietary engine licenses or GPUs on ordinary CI runners. Godot editor/tooling
may be downloaded reproducibly for renderer validation; physical rendering remains a hardware job.

Use a dedicated local hardware test workflow when those resources are necessary.

### Required test types

1. Unit tests.
2. Contract tests.
3. Serialization tests.
4. State-machine tests.
5. Provider-adapter tests.
6. Integration tests.
7. End-to-end tests.
8. Localization tests.
9. Accessibility checks.
10. Security tests.
11. Failure-recovery tests.
12. Performance tests.
13. Hardware-in-the-loop tests.
14. Installation and upgrade tests.

For pure domain logic, target high coverage, preferably at least 85%, while emphasizing meaningful assertions over coverage numbers.

Never weaken tests merely to make a build green.

---

# 12. Implementation milestones

Implement the project in the following sequence.

Each milestone must produce working code, automated tests, documentation, and a clear completion report.

## Milestone 0 — Repository foundation and architecture

### Objectives

Create the repository and establish its engineering foundation.

### Implementation

- Initialize the monorepo.
- Create the initial folder structure.
- Configure Git.
- Create AGENTS.md.
- Create architecture documentation.
- Write initial architectural decision records.
- Configure Python, Kotlin, and C# projects.
- Configure dependency management.
- Add code-quality tools.
- Add pre-commit hooks.
- Add CI workflows.
- Implement development scripts.
- Create shared contract infrastructure.
- Introduce mock implementations for external dependencies.
- Document required development tools.

### Acceptance criteria

- A fresh clone can be bootstrapped using documented commands.
- Python unit tests run.
- Kotlin unit tests run.
- Pure C# tests run.
- Contract validation runs.
- Pre-commit hooks are functional.
- CI configuration is valid.
- Mock mode runs without AI models or cloud credentials.
- Dependency versions are reproducible.

### Deliverables

A healthy repository and a reproducible development environment.

Do not proceed if the basic development workflow is broken.

---

## Milestone 1 — End-to-end native streaming proof of concept

**This is a critical architectural gate.**

### Objectives

Demonstrate that the Windows PC can stream a live rendered 3D scene and audio to a native Kotlin Android application.

### Implementation

- Build a minimal Godot scene.
- Include one animated primitive or placeholder character.
- Capture the rendered video.
- Encode and stream the video.
- Send an audio signal generated by the application.
- Receive video and audio in the Android app.
- Use a native WebRTC client.
- Implement required signaling.
- Implement a basic session lifecycle.
- Implement push-to-talk recording.
- Send microphone audio back to the PC.
- Add connection/disconnection indicators.
- Test reconnection.

Do not spend time creating elaborate 3D assets.

The purpose is validating the riskiest architecture.

### Tests

- Contract tests for signaling.
- State-machine tests.
- Video stream startup test.
- Audio playback test.
- Microphone round-trip test.
- Disconnect/reconnect tests.
- Stream teardown tests.
- Resource cleanup tests.

### Acceptance criteria

- The supported Android Studio emulator receives continuously changing, non-black renderer video
  in the native Kotlin/libwebrtc client.
- Application-owned audio reaches the native client without depending on a PC microphone.
- Emulator microphone audio reaches the PC.
- Disconnecting and reconnecting does not corrupt application state.
- The renderer/media processes tear down without unobserved task failures or stale audio replay.
- A bounded post-startup frame-cadence sample is recorded for development diagnostics.

Aim for 720p at 30 FPS where hardware permits.

If the target cannot be achieved, document measured performance and identify the bottleneck.

### Mandatory decision

At the conclusion of this milestone, formally confirm or revise the development
rendering/streaming architecture using the native-emulator evidence.

Do not proceed with the full teaching application until a viable media architecture is established.

Milestone 1 completion does not prove physical Android compatibility. Do not infer physical-phone,
Wi-Fi, acoustic, hardware-codec, lifecycle, latency/resource, monitor-off, or soak behavior from
the emulator. Those requirements are mandatory release gates in Milestone 9 and must remain
marked not executed until run on target hardware.

---

## Milestone 2 — Session orchestration and shared contracts

### Objectives

Implement the complete application control flow using deterministic fake services.

### Implementation

- Session state machine.
- Contract definitions.
- Cross-language serialization.
- FastAPI orchestration.
- Android session client.
- Godot renderer session controller.
- Event dispatch.
- Error propagation.
- Cancellation.
- Timeouts.
- Session cleanup.
- Logging and correlation IDs.

Create a complete fake lesson:

1. Teacher says a predetermined sentence.
2. Android plays it.
3. Learner records an answer.
4. Fake speech recognizer produces a transcript.
5. Fake dialogue provider creates a reply.
6. Fake speech provider produces audio.
7. Android receives the next teacher turn.

### Acceptance criteria

- The complete turn-taking cycle works.
- No real AI models are needed.
- Every subsystem communicates through validated contracts.
- Invalid payloads are rejected safely.
- Provider failures do not crash the renderer or Android client.
- All state transitions are covered by tests.
- Repeated sessions do not leak resources.

This milestone should establish the functional application skeleton.

---

## Milestone 3 — Local AI and bilingual conversation

### Objectives

Replace mocked AI components with actual local inference.

### Implementation

- Integrate llama.cpp.
- Select and configure an appropriate quantized model.
- Integrate multilingual speech recognition.
- Add language detection.
- Add intent classification.
- Add dialogue policy.
- Add conversation memory.
- Add lesson context.
- Add Bulgarian fallback behavior.
- Add deterministic model failure handling.

Implement explicit behavior for:

- Bulgarian clarification.
- English answers.
- Bulgarian answers requiring English reformulation.
- Requests for repetition.
- Requests for slower speech.
- Vocabulary explanations.
- Ambiguous input.
- Recognition errors.

### Tests

Create curated bilingual fixtures.

Test representative English, Bulgarian, and mixed-language requests.

Verify that a request for clarification does not advance an exercise as though it were a correct answer.

Verify that the LLM cannot produce invalid application control messages.

Test timeouts, model crashes, malformed output, and resource exhaustion.

### Acceptance criteria

- The learner can hold a basic English conversation locally.
- Bulgarian clarification requests work.
- The teacher returns naturally to English.
- Real microphone recordings can be transcribed.
- The selected local LLM generates valid structured outputs.
- No paid API is required.
- Hardware latency and memory benchmarks are recorded.

---

## Milestone 4 — Natural speech and phoneme-aware playback

### Objectives

Implement the speech experience that is central to the application's educational value.

### Implementation

- Integrate natural English TTS.
- Integrate Bulgarian TTS.
- Add deterministic offline fallback.
- Add speech-speed controls.
- Add replay.
- Generate accent-aware IPA.
- Implement phoneme data contracts.
- Implement word alignment.
- Investigate phoneme alignment.
- Implement synchronized subtitles.
- Add word selection and pronunciation inspection in Android.
- Add pronunciation explanations.
- Implement explicit alignment fallback behavior.

### Acceptance criteria

- English teacher responses are spoken aloud.
- Bulgarian explanations are spoken aloud.
- Natural TTS failure activates a working offline fallback.
- Word highlighting follows actual speech when alignment is available.
- IPA transcription can be displayed on demand.
- Individual words can be replayed.
- Subtitle timing remains correct after speed changes.
- Missing alignment does not block playback.
- Both English accent options are handled consistently where supported.

### Testing

Use curated word lists, audio fixtures, IPA regression cases, timing assertions, and manual listening evaluation.

Do not treat phoneme output as correct solely because it is syntactically valid.

---

## Milestone 5 — Teaching engine and learner progression

### Objectives

Make the application an effective tutor instead of a general chatbot.

### Implementation

- Lesson definitions.
- Learning goals.
- Exercise types.
- Difficulty adaptation.
- Vocabulary history.
- Comprehension tracking.
- Gentle correction policy.
- Conversational guidance.
- Scenario selection.
- Local progress persistence.
- Resuming interrupted sessions.
- Learner settings.
- Optional spaced review.

Implement at least four functional guided scenarios:

- Ordering at a café.
- Shopping in a supermarket.
- Traveling through an airport.
- Everyday conversation at home.

Each scenario should define:

- Objectives.
- Target vocabulary.
- Example interactions.
- Difficulty levels.
- Expected learner intents.
- Common misunderstandings.
- Completion conditions.
- Appropriate Bulgarian explanations.

### Acceptance criteria

- A complete guided lesson can be finished.
- Progress persists after restarting the application.
- Lessons adapt to repeated difficulties.
- The learner can ask questions without breaking the exercise.
- Bulgarian assistance does not count as successful English production.
- The teacher provides appropriate corrections.
- Lesson difficulty changes are explainable and testable.
- Tests cover lesson progression and persistence.

---

## Milestone 6 — 3D avatar, lip synchronization, and dynamic scenes

### Objectives

Build the immersive teaching environment.

### Implementation

- Introduce a suitable licensed 3D avatar.
- Add idle animation.
- Add speaking gestures.
- Add listening animation.
- Add basic facial expressions.
- Add audio-driven lip synchronization.
- Add viseme-driven mouth shapes where supported.
- Define the asset catalog.
- Implement scene specifications.
- Implement scene validation.
- Implement a scene planner.
- Add procedural arrangement of objects.
- Add camera presets.
- Add scene transitions.
- Add asset caching.
- Add memory cleanup.
- Add visual fallbacks.

Use deterministic asset IDs.

Never allow the LLM to choose arbitrary file paths, remote downloads, or executable scripts.

### Acceptance criteria

- The teacher is visible in the streamed 3D environment.
- Speaking animation corresponds to teacher audio.
- At least four environments can be assembled.
- The system can change environments in response to lesson context.
- Invalid scene specifications are rejected.
- Missing assets have predictable fallbacks.
- Scene changes do not leak significant GPU memory.
- Runtime scene data remains in memory without requiring generated 3D files on disk.
- Rendering remains usable alongside local inference.

### Performance tests

Measure:

- Scene generation latency.
- Scene transition time.
- Render frame time.
- GPU memory usage.
- Asset loading costs.
- Avatar animation overhead.
- Video encoding overhead.

---

## Milestone 7 — Optional cloud providers and privacy controls

### Objectives

Support paid APIs without weakening the local-first architecture.

### Implementation

Create configurable provider adapters for:

- Text generation.
- Speech recognition.
- Speech synthesis.

Support generic OpenAI-compatible text-generation endpoints where feasible.

Other providers may use dedicated adapters.

Each provider must advertise capabilities and limitations.

Allow independent provider selection per subsystem.

For example:

- Cloud LLM + local STT + local TTS.
- Local LLM + cloud TTS.
- Fully local operation.

### Privacy

- Cloud providers must be opt-in.
- Explain what data will leave the PC.
- Store API credentials using an appropriate operating-system secret store.
- Do not expose secrets to Android.
- Do not log credentials.
- Do not upload recordings to cloud providers unless explicitly configured.
- Provide an offline-only switch.
- Allow complete removal of stored learner data.

### Acceptance criteria

- Local-only operation remains the default.
- Each provider can be switched independently.
- Provider errors are handled gracefully.
- Invalid credentials do not crash the app.
- Cloud requests cannot occur when offline-only mode is enabled.
- Privacy-sensitive data is not written to normal logs.
- Tests verify cloud network access is disabled by default.

---

## Milestone 8 — Windows packaging and Android distribution

### Objectives

Produce an application that can be installed and used without developer tools.

### Windows

Create a repeatable distribution process that packages:

- The Windows launcher.
- The renderer.
- Python orchestration runtime.
- Required local services.
- UI and configuration assets.
- Default lesson content.
- Required runtime dependencies.

Model weights may be downloaded separately during guided first-run setup.

Use pinned model identifiers, checksums, and documented licenses.

Create a simple launcher that:

1. Checks prerequisites.
2. Starts services.
3. Loads the application.
4. Displays pairing information.
5. Shows model and connectivity status.
6. Stops child processes cleanly when exiting.

Do not require the Godot editor or a development Python environment for normal use; package the
exported renderer runtime.

### Android

Produce a signed release APK.

Document:

- Installation.
- Pairing.
- Updating.
- Microphone permissions.
- Wi-Fi requirements.
- Troubleshooting.
- Uninstallation.

### Acceptance criteria

- A clean Windows system can install and launch the application using documented steps.
- Android can connect without development tools.
- A complete lesson works on a release build.
- Shutdown leaves no orphaned processes.
- Local progress survives updates.
- Signing keys remain private.
- Required model downloads have integrity checks.
- Internet access is not necessary during normal lessons.

---

## Milestone 9 — Final reliability, optimization, and release acceptance

### Objectives

Validate that the entire project is stable, comprehensible, secure, and genuinely usable.

### Required testing

Run:

- Complete unit suite.
- Full contract suite.
- Integration suite.
- End-to-end lessons.
- Android UI tests.
- Windows build tests.
- Release packaging tests.
- Provider failure tests.
- Network disconnection tests.
- Privacy/security checks.
- Performance benchmarks.
- Long-running soak tests.
- Manual acceptance tests.

### Required target-hardware acceptance

Execute this bundle during Milestone 9 on a documented physical Android phone and the target
Windows machine. These checks are final release gates, not prerequisites for Milestones 2-8:

- A physical Android device displays the continuously rendered PC scene.
- Teacher audio is audible from the phone and phone microphone audio reaches the PC.
- The lesson media path does not require PC speakers or a PC microphone.
- Streaming operates over the intended local Wi-Fi network with documented firewall setup.
- Pairing, authentication, WSS/signaling security, DTLS-SRTP media, and reconnect behavior pass on
  the physical network path.
- Android background/foreground, interruption, Wi-Fi loss/recovery, disconnect/reconnect, and
  clean teardown preserve session state.
- Android hardware decode and Windows hardware encode are verified where supported; actual codec
  selection and any fallback are recorded.
- The renderer works unfocused, with the monitor off, and while the PC is idle but awake.
- Orientation, acoustic behavior, latency, packet loss, CPU, GPU, RAM, VRAM, thermals, and frame
  cadence are measured under a defined hardware/software/network configuration.
- A 30-minute continuous lesson completes without crashes, stale media, or unbounded resource
  growth.

If suitable target hardware is unavailable, Milestone 9 remains blocked. Emulator, loopback,
mock, compilation, or generated-artifact evidence never satisfies this bundle.

### Performance goals

Treat these as initial targets, not assumed capabilities:

| Metric                   | Initial target                         |
| ------------------------ | -------------------------------------- |
| Video quality            | 720p at 30 FPS                         |
| Teacher response latency | Median under 3 seconds where practical |
| Slow response latency    | Investigate p95 above 6 seconds        |
| Sustained stability      | 30-minute lesson without crash         |
| VRAM                     | Stable operation without OOM           |
| Reconnection             | Recover without restarting the lesson  |
| Rendering                | No sustained frame-time degradation    |
| Speech fallback          | Working without neural TTS             |
| Offline mode             | Fully usable after setup               |

Measure each target under a defined hardware and software configuration.

Collect p50, p95, and relevant worst-case measurements.

Record actual values.

Do not alter measurements to satisfy targets.

If performance goals cannot be met, prioritize:

1. Correctness.
2. Audio intelligibility.
3. Conversation responsiveness.
4. Session stability.
5. Video quality.
6. Visual complexity.

Reduce graphical complexity before sacrificing essential learning functionality.

### Final acceptance scenario

On the documented target Windows PC, launch govor.ai.

Open the signed Android app on the documented physical phone connected through the intended local
Wi-Fi network.

Connect to the PC.

Select the café scenario.

The teacher appears in a rendered environment.

The teacher asks an English question.

The learner listens and asks a clarification question in Bulgarian.

The teacher provides a helpful Bulgarian explanation.

The teacher returns to English.

The learner answers in English.

The application recognizes the response.

The teacher reacts appropriately.

The learner taps an unfamiliar word.

The application displays its IPA and provides word playback.

The learner continues the lesson.

Progress is saved.

The session ends cleanly.

The Android application and Windows processes can subsequently be restarted, and progress remains available.

This complete scenario must work using local models and no paid services.

---

# 13. Automated hardware benchmarking

Because development hardware is expected to be similar to the target RTX 3060 machine, performance testing is a first-class engineering requirement.

Create a standalone benchmark runner.

It should test:

- Local LLM token generation.
- LLM time to first token.
- Speech recognition latency.
- English TTS latency.
- Bulgarian TTS latency.
- Phonemization.
- Speech alignment.
- Rendering.
- Hardware video encoding.
- Concurrent rendering and inference.
- End-to-end response latency.
- Peak VRAM.
- Peak RAM.
- CPU utilization.
- Session stability.

Provide machine-readable results, preferably JSON.

Generate a human-readable benchmark report.

Record hardware, driver, model, quantization, precision, context length, resolution, and test configuration.

Create a baseline comparison mechanism so regressions can be detected.

Do not assert the presence of an NVIDIA GPU without checking.

If the execution environment lacks suitable hardware, run mock benchmarks and clearly mark hardware tests as unexecuted.

Never present simulated benchmark measurements as real hardware performance.

---

# 14. Security and dependency policy

The application contains microphone access and potentially personal conversation history.

Treat those as sensitive.

Requirements:

- Default-deny access to local inference services from the LAN.
- Authenticate all phone-facing control endpoints.
- Protect pairing credentials.
- Use cryptographically secure session identifiers.
- Use secure transport.
- Validate all incoming messages.
- Limit message and audio payload sizes.
- Implement upload timeouts.
- Restrict allowable scene assets.
- Never execute arbitrary LLM output.
- Do not automatically download untrusted executable content.
- Validate downloaded model checksums.
- Avoid unnecessary Windows administrator permissions.
- Minimize Android permissions.
- Never send data to external services without explicit configuration.
- Provide safe logging defaults.

Audit third-party packages, models, voices, and 3D assets.

Document:

- Source.
- Version.
- License.
- Redistributability.
- Required attribution.
- Relevant security issues.

Do not assume all open-weight models or voice packs have permissive licenses.

In particular, evaluate the implications of GPL-licensed phonemization and speech-synthesis implementations before redistribution.

Do not silently replace a dependency with an unlicensed asset or proprietary model.

---

# 15. Documentation requirements

Maintain documentation continuously.

Required files include:

- README.md
- AGENTS.md
- CONTRIBUTING.md
- docs/architecture/overview.md
- docs/architecture/data-flow.md
- docs/architecture/security.md
- docs/architecture/deployment.md
- docs/decisions/
- docs/contracts/
- docs/development/setup.md
- docs/development/commands.md
- docs/testing/strategy.md
- docs/testing/hardware-tests.md
- docs/benchmarks/
- docs/milestones/ROADMAP.md
- docs/milestones/STATUS.md
- docs/user-guide/android.md
- docs/user-guide/windows.md
- docs/troubleshooting/
- THIRD_PARTY_LICENSES.md

AGENTS.md must explain how future Codex agents should work in the repository.

ROADMAP.md must list milestones, dependencies, acceptance criteria, and progress.

STATUS.md must contain the latest verified state of the project, what remains, blockers, and exact commands to resume.

Do not allow implementation changes to invalidate documentation.

---

# 16. Codex working procedure

Follow this procedure for every milestone.

### Step 1 — Inspect

Read:

- AGENTS.md.
- Architecture documentation.
- Current roadmap.
- Current status.
- Relevant contracts.
- Existing tests.
- Recent architectural decisions.

Inspect the actual repository before making assumptions.

### Step 2 — Plan

Prepare an implementation plan covering:

- Files and modules to change.
- Contract changes.
- Dependencies.
- Tests.
- Performance implications.
- Security implications.
- Expected acceptance evidence.

Choose the smallest coherent implementation that satisfies the milestone.

### Step 3 — Implement

Write real production code.

Avoid excessive abstractions that solve hypothetical future requirements.

Use clear names, typed interfaces, and explicit error handling.

Keep commits focused and reviewable.

### Step 4 — Test

Run affected unit tests first.

Then run contract and integration tests.

Run full tests when appropriate.

Run GPU/device tests when hardware is available.

Investigate failures rather than suppressing them.

### Step 5 — Validate

Confirm each milestone acceptance criterion using direct evidence.

Separate:

- Verified passing.
- Verified failing.
- Not executed.
- Blocked by environment.
- Not yet implemented.

### Step 6 — Document

Update:

- Roadmap.
- Status.
- Architecture decisions.
- Relevant interfaces.
- Development instructions.
- Known limitations.
- Benchmark baselines where applicable.

### Step 7 — Report

At the end of each milestone, provide:

1. Summary of implemented functionality.
2. Important design decisions.
3. Files/modules changed.
4. Tests executed and results.
5. Performance results, if applicable.
6. Remaining issues.
7. Commands for verification.
8. Next milestone.

If Git commits are appropriate in the environment, create a focused commit after verification.

### Step 8 — Continue

Proceed to the next milestone when its prerequisites are satisfied.

Stop at genuine architectural blockers rather than constructing further layers on unverified foundations.

Do not repeatedly request user confirmation for routine implementation details.

---

# 17. Definition of done

The project is not complete merely because:

- All planned files exist.
- The code compiles.
- Mock integration tests pass.
- Godot shows an avatar.
- An LLM returns generated text.
- A demo video can be streamed.
- An APK can be produced.

The project is complete only when:

- The Windows host works.
- The native Android client works.
- Real local models work.
- Bilingual conversation works.
- Teacher speech is audible.
- Phoneme-aware learning features work.
- The 3D experience works.
- Dynamic scenes work.
- Session and learning state work.
- Local progress persists.
- Paid providers remain optional.
- Privacy requirements are satisfied.
- Important failure modes are handled.
- Installation instructions are reliable.
- Automated tests pass.
- Hardware acceptance tests pass on available target devices.
- The app is usable without development tools.
- The final acceptance scenario succeeds.

All remaining limitations must be explicitly documented.

A completed project should include a release manifest stating which requirements were verified, on what hardware, using which software versions.

---

# 18. Explicitly out of scope for the initial release

Do not spend early development effort on:

- Public user accounts.
- Multiplayer support.
- Public matchmaking.
- Remote internet streaming.
- Social features.
- Cloud synchronization.
- App-store publication.
- Complex avatar customization.
- Arbitrary AI-generated 3D meshes.
- Photorealistic environments.
- Fully conversational interruption handling.
- Advanced pronunciation scoring without validation.
- Training custom foundation models.
- Monetization.
- Analytics platforms.
- Subscription infrastructure.

The architecture should not prevent future additions, but do not implement them prematurely.

---

# 19. First action

Begin by inspecting the execution environment and determining which prerequisites are already installed.

Then:

1. Create the initial repository structure.
2. Write AGENTS.md.
3. Write the initial architecture and roadmap.
4. Implement Milestone 0.
5. Execute its tests.
6. Report verified results.
7. Start the Milestone 1 streaming feasibility investigation.

**Prioritize obtaining a real, measurable Windows-to-native-Android audiovisual loop before implementing elaborate AI or 3D functionality.**

Continue milestone by milestone toward a complete, production-usable personal application.

The project is called **govor.ai**.

Its guiding principle is:

**A private, patient English teacher that helps a Bulgarian learner become comfortable listening, understanding, and speaking through natural conversation in immersive environments.**
