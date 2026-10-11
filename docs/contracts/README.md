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

`local-ai-dialogue.schema.json` is the closed model-output shape used at the local inference
boundary. It permits only an intent, bounded reply text, `en-GB`/`bg-BG` locale, and a proposed
exercise-advance boolean. It is not a wire envelope because it never leaves the trusted desktop;
the same closed shape is supplied to llama.cpp constrained generation and independently validated
before domain policy applies. An explicit negative fixture proves that an injected renderer action
is rejected.

Speech messages must include locale, format, sample rate, channel count, utterance ID, and timing
reference. Media timing uses integer microseconds relative to the associated media item. Null
alignment means unavailable; it never authorizes guessed timestamps.

Breaking changes require a new protocol version and an ADR. Adding an optional field is allowed
only after all consumers ignore or understand it predictably.
