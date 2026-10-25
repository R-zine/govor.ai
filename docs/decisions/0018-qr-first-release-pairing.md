# ADR-0018: Make local QR scanning the default release pairing path

- Status: accepted; implementation verified in software, physical scan pending
- Date: 2026-10-25
- Scope: post-Milestone 9 maintenance

## Context

The signed Android client previously required a learner to transcribe two endpoints, an
eight-digit one-time code, and a 64-character certificate fingerprint from the Windows console.
That is error-prone and, because the renderer occupies the useful host display, the pairing
information was not visible in the learner-facing UI. The certificate-pinned HTTPS exchange and
stored Android Keystore credential remain the correct trust boundary; only their bootstrap needs
a humane transport.

The QR contains a short-lived secret. It must not be captured in the WebRTC scene, placed on a
command line, logged as a JSON payload, or decoded by an online service. Manual entry is still
valuable for development and diagnostics.

## Decision

The release launcher creates one compact `pairing.bootstrap` version 1 envelope containing the
selected control/media endpoints, one-time code, certificate SHA-256, and absolute expiry. It
encodes the envelope with pinned Segno into a temporary PNG below the protected current-user
security directory. Only the image path is passed to Godot.

The launcher also writes the same bounded envelope as a protected temporary JSON file. It passes
only the PNG and JSON paths to Godot, keeping the one-time code and fingerprint out of the process
command line. Godot starts with an opaque host-only 2D connection screen outside the captured
1280x720 `SubViewport`. It contains instructions, status, expiry countdown, the QR, and a manual
fallback dialog with explicit copy action. The screen is dismissed after `session_started` and is
never part of the phone video. Launcher shutdown deletes both files. The underlying code remains
single-use and expires in ten minutes even if an artifact is copied.

The signed Android app uses pinned ZXing Android Embedded to scan QR codes on-device. Before any
network request it rejects oversized input, unknown envelope or payload fields, unsupported
version/message type, malformed endpoints/code/fingerprint, and expired data. A valid bootstrap
fills the existing connection values and starts the unchanged certificate-pinned HTTPS pairing
exchange. Existing encrypted credentials expose **Reconnect to saved host**; a new scan is
available for a changed host. Release manual fields sit behind **Pair manually**, while debug
builds retain the expanded form.

## Consequences

- First pairing requires pointing the phone at one QR instead of transcribing 80-plus characters.
- Camera permission is requested in context by the scanner and is not needed for later stored-
  credential reconnects.
- The bootstrap is not a second authorization mechanism. Pairing rate, attempt, expiry, device,
  certificate pinning, WSS authentication, and DTLS-SRTP controls are unchanged.
- The launcher still prints manual values so camera failures and development sessions remain
  diagnosable. The host screen exposes the same values only after the user opens its fallback.
- The pre-connect window does not reveal an unrelated 3D scene and the exported Windows player
  carries a project-owned govor.ai icon rather than Godot's default icon.
- Segno (BSD-3-Clause), ZXing Android Embedded (Apache-2.0), and its ZXing Core dependency are
  pinned and recorded in third-party notices.
- A JVM contract test and JSON Schema fixtures prove strict parsing, while a physical-camera scan
  is separately recorded and must not be inferred from compilation or emulator tests.

## Rejected

- Keeping manual transcription as the primary learner flow.
- Encoding only the pairing code and asking the learner to type the endpoints/fingerprint.
- Putting the JSON secret directly on the renderer command line.
- Drawing the QR inside the captured scene, which would send it through WebRTC.
- Uploading a camera frame or QR payload to a cloud decoder.
- A sequence of multiple QRs; the bounded bootstrap fits one standard QR.
