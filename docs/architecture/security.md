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

Android declares only Internet/network-state, microphone, and normal audio-settings permissions.
The audio-settings permission selects the built-in loudspeaker for an active lesson and does not
change system volume. The prior communication route is restored when the session stops. The
release manifest disables cleartext. A debug-only manifest enables it for trusted-LAN development
experiments, and the client requests microphone permission in context before hold-to-talk.

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
It creates a persistent current-user RSA-3072 TLS identity and an eight-digit one-time code with a
ten-minute lifetime. A temporary PNG and matching bounded JSON file in the protected current-user
security directory carry a closed, versioned bootstrap envelope containing the selected LAN
endpoints, code, full SHA-256 fingerprint, and expiry. Godot receives only the paths, renders an
opaque host-only 2D connection screen outside the streamed viewport, and dismisses it when a
session starts; the launcher deletes both files at shutdown. The JSON exists solely so the manual
fallback can display/copy the values without placing the secret in process arguments. The same
values remain in the console for diagnostics. The code is stored only as a PBKDF2-SHA256 salted
digest, is consumed on success, is limited to five failed attempts per client per minute, and
cannot enroll more than eight devices.

Android's camera scanner decodes the QR entirely on-device. The app rejects oversized, expired,
unknown-version, unknown-message, unknown-field, malformed-address/code/fingerprint bootstrap
data before networking, then verifies the full fingerprint for both HTTPS and WSS. Manual entry is
a collapsed diagnostic fallback. The initial HTTPS pairing exchange returns a random device
credential; Android encrypts the credential and its hosts/fingerprint with an Android Keystore
AES-GCM key. The Windows store retains only a salted credential digest in the protected per-user
data directory. Every later phone-facing WebSocket authenticates with the device ID and
credential. Payload/message bounds and existing timeouts remain active after authentication.
WebRTC media continues to use DTLS-SRTP.

The launcher forces the three local providers and `offline_only=true`. llama.cpp, internal
microphone capture, SQLite, and renderer control stay loopback-only. The Windows process tree is
placed in a kill-on-close Job Object and is also stopped explicitly in reverse order. Signing keys
and passwords live only in an ignored ACL-restricted `.secrets` directory and are not copied into
the package or corresponding-source bundle.

Before either LAN gateway starts or a pairing artifact is written, the launcher queries the
Windows NetTCPIP inventory. An advertised address must be RFC1918 and belong to an active physical,
non-virtual adapter with a recognized Windows network category. Disconnected, VPN/virtual,
unidentified, non-RFC1918, loopback, and link-local candidates fail closed. A Private category is
preferred; a Public-category RFC1918 link is allowed with an explicit warning because the category
controls Windows discovery/firewall defaults but does not make that address publicly routable.
Windows' lowest active default-route metric is deterministic within each category;
`--lan-address` can override it only with another address that passes the same checks.

On a Public-category link, the operator must confirm it is the learner's trusted router and permit
the packaged runtime only on the required local network scope. Pairing, rate limits,
certificate-pinned HTTPS/WSS, gateway authentication, and DTLS-SRTP remain mandatory regardless of
profile. Router port forwarding and public-internet exposure remain forbidden. This supports a
host on Ethernet and a phone on Wi-Fi only when the router bridges or routes both links; it does not
bypass guest isolation, VLAN policy, or Windows Firewall.

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

Scene commands add only bounded environment IDs, closed camera/lighting/transition presets, and
objects that are exactly one closed built-in asset or one closed box/cylinder/sphere primitive
with bounded dimensions, color, and transform. Lesson JSON may select only an ID in the current
validated planner. Neither dialogue output nor learner text supplies an object. Godot does not
accept paths, URLs, resource names, scripts, models, textures, assemblies, or downloads. Unknown
built-in IDs are rejected, and the predictable internal fallback is reachable only when an
allow-listed built-in implementation is missing. Avatar commands contain bounded PCM energy
summaries and actual-or-empty viseme cues, not the audio or transcript.

Teacher selection is a separate closed loopback message. JSON Schema plus Python/C# bindings
accept only `elena`, `amira`, or `daniel`; the host maps those IDs to application-owned local/cloud
voice settings. Neither lesson content nor model output can provide a GLB path, resource name, or
voice name. The three GLBs and four built-in backdrop images are reviewed package resources and
are never accepted from environment ZIPs or downloaded at runtime.

Lesson JSON is local content but is still treated as untrusted input at the process boundary. The
loader limits the directory to 64 files and each file to 256 KiB, requires exact fields and bounded
strings/lists, rejects duplicate scenario/exercise IDs and unsupported schema versions, and
constructs immutable domain values before use. The Windows importer accepts only a selected local
JSON or a ZIP of at most 64 JSON entries/4 MiB expanded data. It rejects encrypted entries,
non-JSON members, traversal names, oversized input, existing scenario IDs, and unknown closed scene
templates; it reads entries directly and never extracts archive paths. Files are additive and are
published under a local import lock only after validating the complete combined catalog.

Invalid content fails startup. During runtime, an invalid out-of-band edit is never installed as a
partial catalog: the host keeps its last valid immutable snapshot, reports `reload_error` in local
health, and sends no update. The importer and watcher are local filesystem features; there is no
new LAN endpoint. Lesson data cannot become a path, URL, script, command, or renderer asset ID.
Catalog messages expose only ID, title, description, and display order.

Environment ZIPs are local content and remain untrusted. The importer permits one to 32 JSON
files, caps source/entry/expanded sizes, rejects encryption, traversal and every non-JSON member,
and never extracts an archive path. Exact fields, closed primitive/preset values, numeric bounds,
unique IDs, protected built-in IDs, and the complete resulting catalog are validated before
additive publication under a local lock. A runtime watcher retains its last valid immutable
planner on invalid edits and reports `environment_catalog_status=reload_error`. This path adds no
LAN endpoint and cannot replace application or Godot project files.

Application patches have a separate, stronger boundary because they can replace code. The package
pins an RSA-3072 update public key; its private counterpart stays in ignored ACL-restricted
`.secrets`. The installed verifier authenticates the exact manifest before extraction, accepts
only bounded canonical relative paths and exact listed members, verifies old and new size/SHA-256
values, stages before mutation, and rolls back partial commits. It refuses to patch its own
bootstrap or trust key. Patch archives are never treated as executable input and no update route is
LAN-facing. An optional APK is signature-bound to the patch and staged only; Android performs the
actual visible package-signature/update decision. See ADR-0016.

The host pre-connect management menu adds no administration endpoint. It resolves only four exact
package-owned command names under the trusted install root. Lesson/environment tools retain their
existing local validation boundaries. The application-patch action is a closed renderer exit
signal; the launcher completes managed-process cleanup before it starts the installed signed
updater. No user-selected path is passed from Godot to a shell. See ADR-0021.

The Windows lesson creator talks only to fixed loopback llama.cpp HTTP. Its topic is bounded to 500
characters and treated as untrusted content in the model prompt. The model response is capped,
constrained by the versioned `local-ai-lesson-content` schema, parsed with unknown fields forbidden,
and then validated again as a complete lesson definition. The output shape has no path, persistent
ID, display-order, schema-version, scene-ID, command, URL, or renderer-asset field; generated prose
is never interpreted as any of those. Application code selects the structural fields and publishes
only through the locked additive importer.
Omitted options are deterministic and never cause an extra provider request. The creator adds no
LAN route, cloud fallback, telemetry, or content logging. These controls establish structural and
execution safety; they do not certify generated pedagogical or factual quality.

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
clean-Windows launch, and shutdown paths. On 2026-10-21 the release path also completed first
pairing and stored-credential reuse over the intended private Wi-Fi, authenticated WSS, WebRTC
DTLS-SRTP, background/foreground recovery, Wi-Fi loss/recovery, and explicit reconnect on a
physical phone. The final suite also passes pairing one-time/expiry/rate/device bounds, missing or
invalid device authentication, payload/schema rejection, loopback-only capture/metrics, scene
allow-list, model-integrity, offline/cloud-consent, redaction, and release-manifest checks. The
exact post-audit package passed the physical secure path. No public-internet deployment is
authorized.

The executed Milestone 8 QEMU/WHPX fixture keeps its generated SSH key, DPAPI-protected random
guest password, disks, and logs below ACL-restricted ignored `.cache/m8-vm`. QEMU forwards SSH and
the two release gateways on host loopback only; the host emulator reaches the latter through
`10.0.2.2`. A single host-loopback UDP 18770 forward supports an environment-gated fixture ICE
candidate while media remains DTLS-SRTP. The guest opens only ports 8765/8766 and fixture UDP 18770
for the packaged Python executable on its Private profile. This path added no LAN/public exposure
and creates no physical-network evidence.
