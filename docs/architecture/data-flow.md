# Data flow

## Release connection

1. The Windows launcher inventories active IPv4 adapters; rejects non-physical, non-RFC1918, and
   unidentified links; prefers a Windows Private category; and then follows route metrics unless
   an eligible address was explicitly selected. A Public-category RFC1918 link remains eligible
   with a trusted-router/firewall warning. It then reuses or creates its current-user TLS identity,
   creates a ten-minute one-time pairing code, writes a temporary QR and matching bounded JSON
   bootstrap, and passes only their protected local paths to Godot. Godot opens an opaque 2D
   connection screen above, and outside, the captured 1280x720 media viewport. The screen supplies
   instructions, countdown, QR, and a manual fallback; the console retains the same values for
   diagnostics.
2. Android scans and strictly validates the bootstrap locally, pins its certificate fingerprint,
   and sends the code/device identity to the HTTPS pairing endpoint. The server consumes the code
   and returns a random device credential. Manual release entry remains collapsed unless opened.
3. Android encrypts the hosts, fingerprint, device ID, and credential with Android Keystore. The
   server persists only salted hashes in the protected per-user data directory.
4. Media signaling and lesson control each open WSS and send `gateway.authenticate` before any
   session message. Local inference, microphone capture, progress, and renderer control remain on
   loopback.
5. Later starts reuse the stored credential when the same hosts and optional fingerprint match;
   no pairing code is needed. Replacing the versioned Windows directory leaves that state intact.
6. `session_started` dismisses the 2D host screen and exposes the selected 3D lesson. The launcher
   removes both temporary bootstrap artifacts during shutdown. Their embedded code is already
   single-use and expires after ten minutes.

## Lesson turn

1. Android authenticates to the release LAN gateway and establishes signaling/control. The
   Milestone 2 emulator development path instead uses debug-only `adb reverse` to loopback.
2. Android requests `lesson.catalog`; the host returns the current ordered immutable summary.
   Android selects only an ID from that response. A validated host-side import causes the host to
   push the replacement summary on the same authenticated connection. Before lesson start, the
   Material 3 list and preferences sheets own catalog, accent, and review selection; playback
   actions are not present in this context.
3. The gateway starts a WebRTC media session with the renderer/media service.
4. The host produces a validated teacher response, synthesized audio, and optional timing data.
5. The renderer receives only validated scene/avatar commands and media timing.
6. Android selects its built-in loudspeaker for the connected lesson, receives video and teacher
   audio, then reports playback completion. The active Material 3 overlay exposes progress,
   subtitles, transcript, retry/PTT, and icon menus for replay, speed, pronunciation, and
   disconnect. Disconnect/background teardown restores the prior communication-audio route.
7. Only in `awaiting_learner` may Android enter `recording`.
8. Push-to-talk audio is sent as a bounded authenticated upload or WebRTC track.
9. The host recognizes speech, classifies intent, applies lesson policy, and creates the next turn.

Android's `/v1/control` connection first sends `lesson.catalog.request`, then sends
`session.start` with a scenario from that catalog, English accent, and spaced-review preference,
followed by playback completion, recording start/submission metadata, retry, and cancellation.
`Manage-Lessons.cmd` is a separate local Windows path: its picker passes a selected JSON/ZIP to the
launcher, which validates and additively publishes it into `content/lessons`. The control host
notices that local directory change and sends a new `lesson.catalog`; no unauthenticated LAN
administration endpoint is exposed. A running lesson keeps its prior immutable snapshot.
`Create-Lesson.cmd` is a second same-PC path. It resolves omitted settings deterministically,
sends the bounded topic and resolved content settings to loopback llama.cpp, validates the closed
structured response, adds application-owned IDs/order/scene fields, and hands the complete JSON to
the same importer. The creator does not call a network-facing host route, and the existing watcher
provides the same live Android update.
`Manage-Environments.cmd` is a third same-PC path. Its native picker accepts one ZIP, and the
launcher reads (without extracting) only bounded environment JSON entries. After whole-batch and
combined-catalog validation, it publishes recipes into `content/environments`. The host swaps to
a new immutable planner snapshot on the next poll. The lesson importer/creator then allow the new
environment ID, and the next `session_started` command carries its validated primitive recipe to
the already-running Godot renderer.

## Offline application update

1. The application is stopped and `Apply-Govor-Patch.cmd` selects a local `.govorpatch`/ZIP.
2. The installed, non-patchable bootstrap reads the package-pinned RSA public key and verifies the
   detached signature over the exact manifest bytes before trusting any operation.
3. It checks the source version, exact member set, bounded paths/sizes, old host file hashes, and
   all new payload hashes, then stages the complete payload below the per-user data root.
4. Host operations commit with backups and the target `release.json` last. A later failure restores
   already committed paths. Unlisted imported content and progress/model/credential/TLS state are
   untouched.
5. If present, the verified APK is retained in the per-user updates directory. The user transfers
   and opens it on Android, where the OS checks application/signing/update compatibility and asks
   for confirmation. No patch bytes or administration command cross the lesson LAN gateway.

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

The host also asks the pure scene planner for the selected lesson's validated scene-template
specification and includes it only with `session_started`. Godot validates either closed built-in
asset IDs or closed primitive shapes with bounded colors, dimensions, and transforms, builds the
scene from cached procedural resources, fades from the previous environment, and queues the
replaced node tree for cleanup. No generated `.tscn`, model file, texture, script, or other 3D
resource is loaded or written at runtime.

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

Godot publishes each latest complete 1280x720 RGBA frame into one of two alternating slots in a
fixed Windows-local memory mapping. It fills the inactive slot before atomically committing the
small header, so the previous complete frame stays readable. The aiortc reader verifies the header
did not change during the copy and may asynchronously await a publication for up to 20 ms to avoid
sampling the same frame solely because its 30 fps phase leads the renderer. Application-owned
48 kHz mono PCM uses a bounded 64-block ring of 20 ms blocks. The mapping protocol has writer
generations and publication sequences; incomplete writes are ignored, old video is replaced, and
an audio reader that falls behind resumes from the oldest still-available block. This transport is
process-local and is not a wire contract.

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
