# ADR-0005: Host-owned session control with an outbound renderer client

- Status: accepted
- Date: 2026-10-10
- Milestone: 2

## Context

Milestone 2 needs one deterministic turn cycle across the Windows host, native Android client, and
Godot renderer. The control plane must support strict contracts, timeouts, cancellation, failure
propagation, and cleanup without moving lesson policy into Android or Godot. The Milestone 1 media
gateway already owns WebRTC; adding another network listener inside Godot would enlarge the trusted
surface and blur ownership.

## Decision

The FastAPI host is the sole session authority. Android opens `/v1/control` and sends versioned
session events. A connection owns at most one session, while the host owns the domain state machine,
provider tasks, deadlines, correlation IDs, renderer dispatch, and cleanup registry.

Godot opens an outbound WebSocket to the host's loopback-only `/v1/renderer/control` endpoint. The
host sends only `renderer.command` payloads with an allow-listed action, UUIDs, and bounded integer
microsecond timing. Godot validates the common C# contract, applies the visual state, and returns
`renderer.ack`. It does not receive lesson policy, model output, filesystem paths, URLs, or code.

Provider work runs in cancellable background tasks so the receive loop remains available for
`session.cancel`. Renderer acknowledgement, provider work, teacher playback, learner response, and
recording have explicit deadlines. Disconnect or cancellation stops tasks, resets the renderer,
and removes the active session. Normal logs contain event names and identifiers, not audio or full
transcripts.

The Milestone 2 fake teacher WAV travels in the bounded `teacher.turn` control payload and is
played by Android to prove the entire control skeleton deterministically. Microphone media remains
on WebRTC; the fake recognizer consumes only an ephemeral reference/duration and returns a scripted
transcript. This fake path is not a production STT/TTS or final speech-transport decision.

## Security boundary

Both host control endpoints bind to loopback. The emulator reaches `/v1/control` only through the
debug `adb reverse` path. There is no claim that this unauthenticated cleartext endpoint is safe on
a LAN. Release pairing, device authorization, WSS, rate limits, firewall validation, and the
physical network path remain mandatory Milestone 9 work.

## Consequences

- Domain rules remain framework-independent and Android/Godot remain presentation adapters.
- Renderer loss and provider failures become explicit recoverable errors rather than process
  crashes.
- Shared JSON fixtures exercise Python schema validation and Kotlin/C# decoding.
- Production speech integration may replace the temporary control-payload tone without changing
  state ownership or the renderer command boundary.
- A future multi-device design will require an authenticated session registry rather than the
  current one-session-per-control-connection development model.

## Evidence

- Host integration tests cover a complete fake turn, invalid payloads/transitions, timeouts,
  injected provider failure, cancellation, real dual-WebSocket renderer routing, and 20 repeated
  session teardowns.
- Kotlin and C# tests decode shared version 1 fixtures; Godot's headless self-test validates a
  renderer command.
- `scripts/emulator-renderer-smoke.ps1` completed the control/media turn twice on the API 34
  emulator, including renderer-unavailable recovery, next-turn delivery, microphone return,
  disconnect/reconnect, acknowledgements for every renderer action, and bounded cleanup.

This emulator evidence closes Milestone 2 only. It is not evidence for any physical phone, Wi-Fi,
codec hardware, acoustics, target-machine performance, monitor-off, or soak requirement in
Milestone 9.
