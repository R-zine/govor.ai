# Data flow

## Lesson turn

1. Android authenticates to the release LAN gateway and establishes signaling/control. The
   Milestone 2 emulator development path instead uses debug-only `adb reverse` to loopback.
2. The gateway starts a WebRTC media session with the renderer/media service.
3. The host produces a validated teacher response, synthesized audio, and optional timing data.
4. The renderer receives only validated scene/avatar commands and media timing.
5. Android receives video and teacher audio, then reports playback completion.
6. Only in `awaiting_learner` may Android enter `recording`.
7. Push-to-talk audio is sent as a bounded authenticated upload or WebRTC track.
8. The host recognizes speech, classifies intent, applies lesson policy, and creates the next turn.

Android's `/v1/control` connection sends
`session.start` with an allow-listed scenario, English accent, and spaced-review preference,
followed by playback completion, recording start/submission metadata, retry, and cancellation.
The microphone itself remains on the WebRTC track. In `local` mode, recording start opens a single
bounded capture in the media service; received frames are resampled to 16 kHz mono PCM. Submission
closes the capture and returns an in-memory WAV over a loopback-only internal HTTP endpoint. The
host passes that WAV to whisper.cpp, deletes the recognizer's temporary input/output files, sends a
validated transcript when speech exists, and invokes the bilingual dialogue pipeline.

At lesson start, the host opens or resumes the selected scenario from local SQLite. The dialogue
provider sees the current exercise context, but the pure teaching engine independently evaluates
the validated recognition. Help/Bulgarian/mixed/no-speech turns retain the exercise. An English
production attempt records only structured success/failure and vocabulary counters. The engine
selects the committed correction or next prompt and applies an explainable bounded difficulty
change when appropriate. Every `teacher.turn` carries the resulting progress snapshot. After a
completed lesson's final audio finishes, the host ends the session with reason `completed`.

The host also asks the pure scene planner for the selected scenario's deterministic scene
specification and includes it only with `session_started`. Godot validates the closed IDs and
bounded transforms, builds the scene from cached procedural resources, fades from the previous
environment, and queues the replaced node tree for cleanup. No generated `.tscn`, model file, or
other 3D file is written at runtime.

The local dialogue adapter sends the recognized utterance, lesson context, deterministic intent
hint, and at most the configured number of recent turns to llama.cpp. Closed structured output is
parsed, then the domain policy can reject unsafe locale/progress choices and use a deterministic
fallback. The bounded WAV in `teacher.turn` is local synthesized PCM16 speech. The speech router
uses Kokoro for explicit `en-GB`/`en-US`, Piper for `bg-BG`, and deterministic eSpeak NG when a
neural provider fails. The turn also carries exact word/IPA character ranges and nullable model
timing. Android plays the WAV with `AudioTrack`; playback-head frames define media time for
subtitle highlighting. Missing alignment disables highlighting without blocking playback.

When explicitly enabled, the provider router may instead send the bounded transcript, lesson
context, and recent history to the selected cloud dialogue endpoint; the bounded utterance WAV to
the selected cloud recognizer; and teacher response text to the selected cloud speech endpoint.
These choices are independent. No cloud request is possible while `offline_only` is true, and
microphone audio additionally requires explicit upload consent. Credentials are fetched from
Windows Credential Manager for the request and never enter a wire envelope. Cloud speech alignment
is null unless a future adapter can prove provider-originated timing.

For each synthesized teacher turn, the scene planner samples the actual mono PCM16 WAV into a
bounded 40 ms energy envelope. If the provider returned phoneme spans, it maps their real
microsecond offsets to a closed viseme sequence; otherwise `viseme_source` is `none` and the
sequence is empty. The `teacher_speaking` renderer command carries only duration, energy, and
optional visemes. Android receives the original audio independently, so renderer animation cannot
alter playout or lesson completion.

After the host enters `awaiting_learner`, Android may replay the cached full turn locally without
emitting another lesson-completion event. Selecting an annotated word sends
`teacher.word_replay_requested`; the host validates the active turn/index, synthesizes only that
word at the selected rate, and returns `teacher.word_audio` without changing session state.

For every state change, the host dispatches an allow-listed `renderer.command` over a separate
loopback WebSocket opened by Godot and waits for `renderer.ack`. Renderer loss becomes a
recoverable session error. Provider calls do not block the receive loop, so cancellation can stop
in-flight work. Playback, learner-response, recording, provider, and renderer acknowledgement
timeouts all converge on explicit recoverable states.

For the Milestone 1 renderer experiment, Godot publishes its latest complete 1280x720 RGBA frame
into a fixed Windows-local memory mapping. Application-owned 48 kHz mono PCM uses a bounded
64-block ring of 20 ms blocks. The aiortc peer reads these sources and sends WebRTC tracks to
Android. The mapping protocol has writer generations and publication sequences; incomplete writes
are ignored, old video is replaced, and an audio reader that falls behind resumes from the oldest
still-available block. This transport is process-local and is not a wire contract.

The initial state sequence is:

`ready -> teacher_speaking -> awaiting_learner -> recording -> processing -> teacher_speaking`

Overlapping recording in `processing` is rejected. Retried control events carry stable identifiers
and are idempotent. Disconnect transitions to `reconnecting`; lesson state remains on the host.

## Sensitive data

Raw microphone audio is held only long enough to process an utterance and is not persisted by
default. Normal logs contain event names, timing, correlation IDs, and error classes—not audio,
credentials, or full transcripts. The transcript is sent to the active Android session but is not
written to normal logs. Conversation memory is session-local, bounded, and cleared with its lesson
service. Progress is stored locally in SQLite as settings and structured counters; raw audio and
complete transcript text are not persisted. A local CLI can view/export those counters or delete
history while preserving explicit settings. `DeleteAll` removes history and restores settings to
defaults. Optional cloud processing means the selected third party receives only the categories
listed above; its retention and deletion terms are external and must be reviewed before opt-in.

## Timing

`media_time_us` is a signed 64-bit integer measured from media-item start. Word, phoneme, viseme,
and playback events reference the same item and time base. Missing alignment is represented as
absent/null data. Android falls back from phonemes to words and then untimed playback; Godot uses
the PCM energy envelope without inventing a viseme timeline.
