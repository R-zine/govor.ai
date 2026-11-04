# Data flow

## Release connection

1. The Windows launcher inventories active IPv4 adapters; rejects non-physical, non-RFC1918, and
   unidentified links; prefers a Windows Private category; and then follows route metrics unless
   an eligible address was explicitly selected. A Public-category RFC1918 link remains eligible
   with a trusted-router/firewall warning. It then reuses or creates its current-user TLS identity,
   creates a ten-minute one-time pairing code, writes a temporary QR and matching bounded JSON
   bootstrap, and passes only their protected local paths to Godot. Godot opens an opaque 2D
   connection screen above, and outside, the captured 1280x720 media viewport. The screen supplies
   instructions, countdown, QR, a closed teacher selector, and a manual fallback; the console
   retains the same pairing values for diagnostics. The selected teacher profile is persisted in
   Godot's per-user settings and sent to the loopback host after renderer registration.
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
2. Android requests `lesson.catalog`; the host returns the current ordered immutable lesson
   summary, validated environment choices, the closed teacher-profile catalog, and the current
   teacher ID. Android selects only
   advertised IDs. A pre-lesson `teacher.profile.select` updates the host voice selection and the
   Godot model over loopback, then returns the updated catalog as confirmation. A validated
   host-side import also pushes the replacement summary on the same authenticated connection.
   Beside the selector, Android may send one bounded pre-lesson `lesson.create.request`; the host
   uses loopback llama.cpp and the existing atomic importer, returns `lesson.create.result`, then
   broadcasts the refreshed catalog. No file/path or model-controlled identifier crosses the LAN.
   Before lesson start, the Material 3 list and preferences sheets own lesson, teacher, accent,
   and review selection; playback actions are not present in this context.
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

Android's `/v1/control` connection first sends `lesson.catalog.request`, may send a closed
`teacher.profile.select`, then sends `session.start` with a scenario from that catalog, English
accent, and spaced-review preference, followed by playback completion, recording start/submission
metadata, retry, and cancellation.
`Manage-Lessons.cmd` is a separate local Windows path: its picker passes a selected JSON/ZIP to the
launcher, which validates and additively publishes it into `content/lessons`. The control host
notices that local directory change and sends a new `lesson.catalog`; no unauthenticated LAN
administration endpoint is exposed. A running lesson keeps its prior immutable snapshot.
`Create-Lesson.cmd` and the authenticated phone lesson-creator sheet are two UIs over the same
bounded operation. They resolve omitted settings deterministically,
sends the bounded topic and resolved content settings to loopback llama.cpp, validates the closed
structured response, adds application-owned IDs/order/scene fields, and hands the complete JSON to
the same importer. The phone uses the existing paired WSS control channel rather than a separate
administration endpoint, and the host provides the same live Android update.
`Manage-Environments.cmd` is a third same-PC path. Its native picker accepts one ZIP, and the
launcher reads (without extracting) only bounded environment JSON entries. After whole-batch and
combined-catalog validation, it publishes recipes into `content/environments`. The host swaps to
a new immutable planner snapshot on the next poll. The lesson importer/creator then allow the new
environment ID, and the next `session_started` command carries its validated primitive recipe to
the already-running Godot renderer.

All three Windows entry points are available from the host pre-connect **Content & updates** menu
as exact package-owned local commands. Lesson creation and confirmed deletion of the active
lesson are also available from the phone through bounded authenticated control messages. Import
and patch paths remain local-only.

## Offline application update

1. The user chooses **Apply application patch** from the host menu (or runs the installed command
   directly). The launcher stops every managed process, then `Apply-Govor-Patch.cmd` selects a
   local `.govorpatch`/ZIP.
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
specification and includes it only with `session_started`. Godot validates either a closed built-in
environment ID or closed primitive shapes with bounded colors, dimensions, and transforms. A
built-in ID selects one packaged photographic backdrop; an installed recipe builds only cached
primitive resources. Godot fades from the previous environment and queues the replaced node tree
for cleanup. No generated `.tscn`, model file, texture, script, or other 3D resource is loaded or
written at runtime.

The local dialogue adapter sends the recognized utterance, lesson context, deterministic intent
hint, and at most the configured number of recent turns to llama.cpp. Closed structured output is
parsed, then the domain policy can reject unsafe locale/progress choices and use a deterministic
fallback. The model's strict JSON boolean assesses the answer's meaning against the active question
and goal. The local lesson service passes that verdict to `TeachingEngine`, whose language/help
guards and progression rules still apply. If inference/parsing fails, the engine receives no
semantic verdict and uses its limited literal matcher. A valid false verdict never falls back to
keyword matching. The bounded WAV in `teacher.turn` is local synthesized PCM16 speech. The speech router
uses the current teacher profile to choose a female or male Kokoro voice for explicit
`en-GB`/`en-US`. All profiles use the substantially clearer neural Piper Dimitar voice as the base
for `bg-BG`. Elena and Amira receive a bounded duration-preserving pitch presentation of that
neural waveform; Daniel receives the original waveform. Provider failure always uses normal
Bulgarian eSpeak `bg`, never the previously unintelligible `bg+f3` variant. The turn also carries exact
word/IPA character ranges and nullable model timing. Android plays the WAV with `AudioTrack`;
playback-head frames define media time for subtitle highlighting. Missing alignment disables
highlighting without blocking playback.

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

Phone creation requests enter a host-owned job, not the current socket's cancellation scope.
Authenticated-device identity selects the recoverable latest status. `lesson.create.status` goes
to that device, `renderer.lesson_creation` supplies bounded host display text/state, and successful
publication broadcasts the new catalog. Android re-queries on reconnect. Phone lock does not
cancel generation; host shutdown cancels it and clears in-memory status.

Mixed teacher replies are segmented by Latin/Cyrillic script before local synthesis. Each span
uses its language voice, selected teacher, and English accent. Resampled PCM and actual timing
are combined into one teacher turn, preserving exact character offsets and explicit null timing.
Android accepts the retained language on each pronunciation independently of the overall reply
locale, so an English example inside Bulgarian help remains playable and keeps its English IPA.

**Leave lesson** sends `session.cancel` over the existing connection. Host cleanup resets Godot;
the renderer returns to its pre-lesson screen. Android clears the active lesson and reloads the
catalog while the WebRTC peer remains connected.

**Delete lesson** instead sends `lesson.delete.request` with only the active session UUID after
a separate named confirmation. The host verifies socket/session ownership, completes the same
lesson cleanup, then resolves the actual lesson file under its trusted content directory and
deletes it under the import lock. Remaining content is validated first and the last lesson is
protected. A replacement catalog is broadcast immediately; a failure is a bounded selector error.
The learning database and the media/control connection remain available.

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
