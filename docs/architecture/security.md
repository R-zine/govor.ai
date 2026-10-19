# Security architecture

The threat boundary is the phone-facing LAN gateway. Local model and database services bind only
to loopback. Before the gateway may bind to a LAN address it must have pairing, authentication,
payload limits, timeouts, rate limits, and encrypted transport.

## Current development posture

The fake and local hosts bind to `127.0.0.1` by default. `scripts/dev.ps1` refuses a LAN control
bind because the ordinary development path deliberately has no release pairing/TLS lifecycle.
This makes development usable through `adb reverse` without pretending the debug control endpoint
is safe for a phone-facing LAN.

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

## Release gateway posture

The Milestone 8 launcher starts separate HTTPS/WSS control and media gateways on ports 8765/8766.
It creates a persistent current-user RSA-3072 TLS identity, prints its SHA-256 fingerprint, and
creates an eight-digit one-time code with a ten-minute lifetime. The code is stored only as a
PBKDF2-SHA256 salted digest, is consumed on success, is limited to five failed attempts per client
per minute, and cannot enroll more than eight devices.

Android verifies the full user-entered certificate fingerprint for both HTTPS and WSS. The initial
HTTPS pairing exchange returns a random device credential; Android encrypts the credential and its
hosts/fingerprint with an Android Keystore AES-GCM key. The Windows store retains only a salted
credential digest in the protected per-user data directory. Every later phone-facing WebSocket
authenticates with the device ID and credential. Payload/message bounds and existing timeouts
remain active after authentication. WebRTC media continues to use DTLS-SRTP.

The launcher forces the three local providers and `offline_only=true`. llama.cpp, internal
microphone capture, SQLite, and renderer control stay loopback-only. The Windows process tree is
placed in a kill-on-close Job Object and is also stopped explicitly in reverse order. Signing keys
and passwords live only in an ignored ACL-restricted `.secrets` directory and are not copied into
the package or corresponding-source bundle.

This release path is distinct from the debug token path. The release manifest disallows cleartext,
and no certificate-verification bypass exists. Certificate rotation, device revocation UI, and
public-internet exposure are out of scope; the gateway must remain on a trusted private LAN.

llama.cpp and the media capture API also bind only to loopback. The host rejects non-loopback
model/capture URLs. Model output is untrusted: generation uses a closed JSON schema, Pydantic
forbids extra fields, and domain policy—not the model—decides whether an exercise may advance. No
model field can become a renderer action, path, URL, tool call, or command. whisper.cpp receives an
ephemeral per-utterance WAV and writes bounded JSON under ignored `.cache`; both files are removed
in a `finally` path. Normal logs and benchmark artifacts omit raw audio and transcript text.

The Milestone 5 SQLite database is also local to the trusted Windows user and has no listener. Its
schema accepts scenario/exercise identifiers, counters, settings, vocabulary items from committed
content, review dates, and closed difficulty reasons only; it has no raw-audio or transcript-text
column. Automated local-AI and emulator smokes use an isolated cache database and remove it so they
cannot alter the learner's development history. History deletion requires an explicit CLI
confirmation flag. Release packaging stores it below `%LOCALAPPDATA%\govor.ai\progress`, separate
from the replaceable versioned installation directory.

Milestone 7 keeps `offline_only=true` and all three provider selectors local by default. Cloud
adapter construction is rejected while that switch is set, and every adapter rechecks an outbound
policy immediately before credential access or HTTP. Recognition has a separate microphone-upload
consent gate. Compatible endpoints must use credential-free HTTPS URLs. API credentials are
stored as current-user generic credentials in Windows Credential Manager; settings contain only a
bounded target name. Secrets never enter Android contracts, command lines, environment variables,
health metadata, exception text, or normal logs. Authentication, rate-limit, transport, and
malformed-response failures become typed provider failures rather than process crashes. No cloud
call was used as acceptance evidence; deterministic tests use an in-process mock transport.
Complete learner-data deletion resets settings and uses SQLite secure deletion plus compaction so
deleted structured rows are not retained in database free pages.
Successful cloud responses are streamed through explicit 64 KiB JSON or 1.5 MiB WAV ceilings
before parsing, so an untrusted endpoint cannot bypass payload bounds with a large response.

Godot's Milestone 2 control client also opens an outbound loopback WebSocket; the renderer opens no
listener. It accepts a closed action set, validates UUIDs and integer-microsecond bounds, and
acknowledges commands. This loopback connection relies on the trusted desktop-user boundary and is
not a LAN authentication mechanism.

Milestone 6 scene commands add only closed environment, camera, lighting, transition, and asset
IDs with bounded transforms. The host derives the specification from a committed scenario
allow-list; neither dialogue output nor learner text supplies an asset. Godot's procedural catalog
does not accept paths, URLs, resource names, scripts, or downloads. Unknown wire IDs are rejected,
and the predictable internal fallback is reachable only when an allow-listed catalog entry is
missing from the renderer implementation. Avatar commands contain bounded PCM energy summaries
and actual-or-empty viseme cues, not the audio or transcript.

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

The unauthenticated control path remains loopback-only and the long development token remains a
cleartext feasibility mechanism, not release pairing. Milestone 8 software/emulator evidence covers
the implemented release certificate, pairing, stored-credential, authenticated WSS, update,
clean-Windows launch, and shutdown paths. The physical private-network path, firewall behavior,
phone key storage, lifecycle recovery, and abuse behavior still require the Milestone 9
release-security gate. No public-internet deployment is authorized.

The executed Milestone 8 QEMU/WHPX fixture keeps its generated SSH key, DPAPI-protected random
guest password, disks, and logs below ACL-restricted ignored `.cache/m8-vm`. QEMU forwards SSH and
the two release gateways on host loopback only; the host emulator reaches the latter through
`10.0.2.2`. A single host-loopback UDP 18770 forward supports an environment-gated fixture ICE
candidate while media remains DTLS-SRTP. The guest opens only ports 8765/8766 and fixture UDP 18770
for the packaged Python executable on its Private profile. This path added no LAN/public exposure
and creates no physical-network evidence.
