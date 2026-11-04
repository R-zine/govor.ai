# Contracts

Version 1 schemas live in `packages/contracts/schemas/v1`. Every cross-process message contains:

- `protocol_version` (`1.0` initially)
- `message_type`
- UUID `correlation_id`
- validated object `payload`

Positive and negative fixtures live in `tests/fixtures/contracts`; `tests/contracts` validates the
schema documents and fixtures. Typed bindings exist in Python, Kotlin, and C#. The bindings remain
small and hand-maintained, while the automated compatibility gate validates the same teacher-turn
and renderer-command fixtures through JSON Schema and the Kotlin/C# decoders. Any contract change
must update schemas, bindings, shared fixtures, and negative tests together.

`control-message.schema.json` is the closed Milestone 2 control union. It covers Android session
events, host state/turn/error events, and the loopback Godot command/acknowledgement exchange.
Unknown message types and payload fields are rejected. Session, turn, utterance, command, event,
and correlation identifiers are UUIDs; media durations and offsets are integer microseconds.
The renderer may send `renderer.teacher_profile_selected` after registration; its payload is one
closed profile ID (`elena`, `amira`, or `daniel`). It carries no path or voice name. The host uses
the same selection for visual-state reporting and speech presentation. `lesson.catalog` also
advertises those closed profile IDs and the current selection to authenticated Android clients.
Before a lesson, Android may send `teacher.profile.select`; the host rejects unadvertised IDs and
mid-lesson changes, forwards the closed ID to Godot, and confirms it with a replacement catalog.
The same catalog advertises bounded environment IDs/display names. Before a lesson, a paired phone
may send `lesson.create.request` with a required bounded topic and optional closed difficulty,
advertised environment ID, and one-to-eight exercise count. `lesson.create.result` contains either
the application-owned installed lesson identity/options or a bounded failure message; it never
contains a path, command, model name, or generated lesson body.

`lesson.create.status.request` has an empty payload and queries the authenticated device's latest
host-owned job. `lesson.create.status` carries a nullable UUID job ID (null only for `idle`), a
closed `idle`/`generating`/`created`/`failed` state, bounded display text, and a matching terminal
result object or null. The host retains this snapshot across phone socket loss. The existing
standalone `lesson.create.result` remains for immediate rejected requests. The loopback-only
`renderer.lesson_creation` carries only the closed state and bounded display text for host UI.

`lesson.delete.request` is an additive version 1 active-session action with only `session_id`.
The host requires that session to belong to the receiving control socket and derives its lesson;
it accepts no scenario ID, filename, or path. Confirmed deletion ends the session using the
existing `session.ended` event, removes the definition under the import lock, and broadcasts
`lesson.catalog`. A failed removal uses the existing bounded `error` shape. Both new host and
client are required to expose this action; an older host rejects the unknown request safely.

`gateway-auth-message.schema.json` is the closed Milestone 8 release-pairing contract. A
`pairing.request` contains the one-time eight-digit code, UUID device ID, and bounded device name;
`pairing.ok` returns that device ID plus a random bounded credential. Subsequent control and media
WebSockets begin with `gateway.authenticate`, carrying the device ID and credential inside the
normal versioned envelope. Invalid codes, unknown fields, and malformed identifiers are rejected
before dispatch. The debug development token remains outside this release lifecycle.

`pairing-bootstrap.schema.json` is the closed QR bootstrap envelope. It carries bounded control
and media `host:port` values, the eight-digit code, uppercase certificate SHA-256, and Unix expiry.
It is generated into a temporary local PNG and decoded entirely on Android before the existing
HTTPS pairing contract runs. Unknown envelope/payload fields, malformed values, oversized input,
and expired bootstraps are rejected. It grants no authority beyond the existing one-time code.

Milestone 4 extends the same version with understood additive fields and closed message variants.
`teacher.turn` contains bounded PCM16 WAV, an explicit sample rate, exact pronunciation ranges,
accent-specific IPA, nullable provider-derived word/phoneme spans, and `fallback_used`.
`teacher.word_replay_requested` identifies an active turn/word plus bounded rate;
`teacher.word_audio` returns one bounded isolated-word WAV. Android and Python validate references,
duration, locale, and audio metadata before use.

`local-ai-dialogue.schema.json` is the closed model-output shape used at the local inference
boundary. It permits only an intent, bounded reply text, `en-GB`/`bg-BG` locale, and a semantic
answer-acceptance boolean named `advance_exercise`. Strings/numbers cannot substitute for JSON
booleans. The local service applies that verdict through the domain's language/help guards and
one-exercise progression rules (ADR-0022); only unusable model output invokes literal fallback.
It is not a wire envelope because it never leaves the trusted desktop;
the same closed shape is supplied to llama.cpp constrained generation and independently validated
before domain policy applies. An explicit negative fixture proves that an injected renderer action
is rejected.

`local-ai-lesson-content.schema.json` is the closed structured-output shape used by the local
lesson creator. It contains bounded lesson prose, examples, misunderstandings, and one to eight
exercises, but deliberately omits install paths, IDs, schema version, display order, and scene
selection. Application code supplies those fields and validates the assembled object against
`lesson-definition.schema.json` before publication. A negative fixture proves that an injected
application command is rejected.

`environment-definition.schema.json` is the data-only local environment recipe. It permits
bounded IDs, display text, closed camera/lighting/transition presets, teacher placement, and one
to 64 colored box/cylinder/sphere objects. Runtime validation additionally enforces exact fields,
finite numeric values, equal X/Z cylinder diameter, unique instance/scene/environment IDs, and
catalog collisions. It contains no executable or external-resource field and is transported to
Godot only after translation into the scene portion of `renderer.command`.

`application-patch-manifest.schema.json` describes the offline signed update file boundary. It
binds an exact source/target pair, closed add/replace/delete host operations with old/new sizes and
SHA-256 values, and an optional Android APK identity/digest. Runtime validation additionally
requires canonical traversal-free paths, Windows-case uniqueness, exact archive membership, the
pinned RSA signature, base-file matches, and a non-patchable bootstrap/trust key. It is not a wire
envelope and is never accepted through a LAN endpoint.

Speech messages must include locale, format, sample rate, channel count, utterance ID, and timing
reference. Media timing uses integer microseconds relative to the associated media item. Null
alignment means unavailable; it never authorizes guessed timestamps.

Milestone 5 adds optional scenario/settings fields to `session.start`, with safe café/GB/no-review
defaults for older version 1 development clients. The host resolves scenario IDs against the
committed allow-list. `teacher.turn.lesson_progress` is additive and includes bounded exercise
counts, difficulty, completion status, resume state, and an optional closed difficulty-change
reason. It contains no learner utterance or audio. Python, Kotlin, C#, JSON Schema, and the shared
teacher-turn fixture understand the same shape.

Milestone 6 adds optional `scene` and `avatar_animation` fields to `renderer.command`. A scene is
valid only on `session_started`; it uses bounded environment IDs, closed presets, exactly one
closed built-in asset or primitive per object, and bounded numeric transforms. Avatar animation
is valid only on `teacher_speaking`; it carries
duration, a bounded PCM-derived energy envelope, a closed gesture/expression, and either real
provider-aligned viseme cues or an empty list with source `none`. A negative shared fixture proves
that an arbitrary relative asset path is rejected.

Breaking changes require a new protocol version and an ADR. Adding an optional field is allowed
only after all consumers ignore or understand it predictably.
