# Security architecture

The threat boundary is the phone-facing LAN gateway. Local model and database services bind only
to loopback. Before the gateway may bind to a LAN address it must have pairing, authentication,
payload limits, timeouts, rate limits, and encrypted transport.

## Current development posture

The deterministic mock host binds to `127.0.0.1` by default. `scripts/dev.ps1` refuses a LAN bind
because pairing and TLS are not implemented yet. This makes the mock usable locally without
pretending it is safe for a phone connection.

The Milestone 2 Android control check reaches that loopback listener only through debug-only
`adb reverse`; `/v1/control` is not authenticated and must not be exposed on a LAN. It caps messages
at 1 MiB, strictly validates message-specific payloads, bounds utterance duration to 30 seconds,
uses per-step timeouts, and returns generic validation errors that do not echo untrusted content.
The fake recording submission contains only an ephemeral WebRTC reference and duration, not raw
microphone bytes.

Android declares only Internet/network-state and microphone permissions. The release manifest
disables cleartext. A debug-only manifest enables it for trusted-LAN development experiments,
and the client requests microphone permission in context before hold-to-talk.

`scripts/media-dev.ps1` requires an explicit insecure-LAN switch and a pre-shared token of at least
32 characters. The WebSocket authenticator uses constant-time comparison and enforces a 1 MiB
message limit; WebRTC media is DTLS-SRTP. The signaling channel is still cleartext and the token is
not a complete pairing lifecycle, so this server and APK are not release-safe.

The Godot media handoff uses named memory mappings in the current Windows session. It
opens no socket, is not reachable from the LAN, contains only transient rendered pixels and the
application-owned PCM ring, and disappears when the last process handle closes. It is not an
authentication boundary: the renderer and media peer must run as the same trusted desktop user.

Godot's Milestone 2 control client also opens an outbound loopback WebSocket; the renderer opens no
listener. It accepts a closed action set, validates UUIDs and integer-microsecond bounds, and
acknowledges commands. This loopback connection relies on the trusted desktop-user boundary and is
not a LAN authentication mechanism.

## Required controls

- Pair using a short-lived code/QR bootstrap and generate a cryptographically random device key.
- Store the device credential with Android Keystore and Windows credential protection.
- Authenticate WebSocket and HTTP requests; authorize one device per lesson.
- Use WSS/HTTPS and WebRTC DTLS-SRTP. Never disable certificate verification permanently.
- Limit SDP to 1 MiB, ICE candidates to 8 KiB, control messages to 1 MiB, and audio submissions to
  an explicitly configured duration and byte limit.
- Validate JSON before dispatch. LLM output can select only allow-listed actions/assets and never
  becomes code, a path, a URL, or a shell command.
- Redact secrets and personal content. Do not save recordings or full transcripts by default.
- Cloud networking remains absent/disabled unless the learner explicitly selects a provider.

The Milestone 2 security review deliberately keeps unauthenticated control on loopback and rejects
LAN binding. Pairing, certificate lifecycle, abuse/rate limits, device authorization, and firewall
rules remain unimplemented release controls. The current host is not production-ready, and the
physical-network path must pass the Milestone 9 release-security gate.
