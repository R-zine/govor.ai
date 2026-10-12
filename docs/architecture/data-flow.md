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
`session.start`, playback completion, recording start/submission metadata, retry, and cancellation.
The microphone itself remains on the WebRTC track. In `local` mode, recording start opens a single
bounded capture in the media service; received frames are resampled to 16 kHz mono PCM. Submission
closes the capture and returns an in-memory WAV over a loopback-only internal HTTP endpoint. The
host passes that WAV to whisper.cpp, deletes the recognizer's temporary input/output files, sends a
validated transcript when speech exists, and invokes the bilingual dialogue pipeline.

The local dialogue adapter sends the recognized utterance, lesson context, deterministic intent
hint, and at most the configured number of recent turns to llama.cpp. Closed structured output is
parsed, then the domain policy can reject unsafe locale/progress choices and use a deterministic
fallback. The bounded WAV in `teacher.turn` is local synthesized PCM16 speech. The speech router
uses Kokoro for explicit `en-GB`/`en-US`, Piper for `bg-BG`, and deterministic eSpeak NG when a
neural provider fails. The turn also carries exact word/IPA character ranges and nullable model
timing. Android plays the WAV with `AudioTrack`; playback-head frames define media time for
subtitle highlighting. Missing alignment disables highlighting without blocking playback.

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
service; progress is stored locally in SQLite in a later milestone.

## Timing

`media_time_us` is a signed 64-bit integer measured from media-item start. Word, phoneme, viseme,
and playback events reference the same item and time base. Missing alignment is represented as
absent/null data; consumers fall back from phonemes to words and then to untimed playback.
