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

In the Milestone 2 deterministic skeleton, Android's `/v1/control` connection sends
`session.start`, playback completion, recording start/submission metadata, retry, and cancellation.
The microphone itself remains on the WebRTC track. The unmistakably fake recognizer intentionally
uses only the bounded utterance duration/reference and returns a scripted transcript; this proves
orchestration, not speech recognition. A short bounded WAV tone is carried in `teacher.turn` and
played by Android solely for the fake control-flow proof. Production speech/media routing is a
Milestone 4 concern and this development tone is not a TTS architecture commitment.

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
credentials, or full transcripts. The scripted transcript is sent to the active Android session
but is not written to normal logs. Progress is stored locally in SQLite in a later milestone.

## Timing

`media_time_us` is a signed 64-bit integer measured from media-item start. Word, phoneme, viseme,
and playback events reference the same item and time base. Missing alignment is represented as
absent/null data; consumers fall back from phonemes to words and then to untimed playback.
