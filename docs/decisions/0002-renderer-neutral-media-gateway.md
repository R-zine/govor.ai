# ADR-0002: Prove native WebRTC through a renderer-neutral media boundary

- Status: accepted for Milestones 2-8; target-hardware release path remains a Milestone 9 gate
- Date: 2026-10-08
- Updated: 2026-10-09 after the Godot selection in ADR-0003

## Context

The highest-risk integration is continuous Windows video/application audio to a native Kotlin
Android client plus microphone audio in the reverse direction. Binding the application protocol to
one engine's WebRTC package would combine renderer, signaling, codec, and Android interoperability
risk before any of them had evidence.

## Decision

Own a small versioned signaling contract and keep media transport behind a renderer-neutral local
boundary. aiortc is the Windows WebRTC peer. A renderer supplies only its latest complete
1280x720 RGBA frame and application-owned PCM through two Windows named memory mappings.

Video uses a single latest-frame slot. Audio uses a bounded ring of 20 ms, 48 kHz mono blocks.
Publication sequences reject torn writes, writer-generation values permit renderer restart, and a
lagging reader skips stale data rather than growing memory. A newly attached audio reader begins
after the current write position so reconnect cannot replay a retained block after PCM production
has stopped. aiortc owns pacing, silence fallback, encoding, DTLS-SRTP, and the Android-facing
peer connection.

The current renderer is Godot 4.7.2 .NET, selected in ADR-0003. Changing renderers must not alter
the Android signaling or media contracts.

The bridge is the accepted development path. It performs GPU-to-CPU readback and a managed copy
before software-visible aiortc encoding. Windows hardware encoding is not proven. If Milestone 9
target-hardware measurements miss the release gate, first evaluate an asynchronous Godot
GDExtension or a dedicated native capture/hardware-encoding bridge.

Android libwebrtc remains pinned to `io.github.webrtc-sdk:android:150.7871.01` for this experiment,
including its BSD and third-party notices.

## Rejected

- A WebView receiver: violates the native-client requirement.
- Engine-owned signaling/WebRTC: couples the wire protocol and native client to a renderer plugin.
- Building libwebrtc from source before feasibility evidence: disproportionate checkout and build
  cost for the first gate.
- Sending raw renderer frames over a LAN socket: expands the attack surface without solving codec
  or latency requirements.

## Milestone 9 release evidence still required

Physical Android video/audio/microphone, hardware decoder evidence, Windows hardware encoder
evidence, reconnect/teardown, unfocused/monitor-off behavior, LAN security, latency/resource
measurements, and a 30-minute stability run.

## Evidence to date

- Real aiortc loopback negotiates generated 1280x720 video, 48 kHz audio, and reverse audio.
- The native Android client completed video/audio/microphone and reconnect checks on an API 34
  emulator through `adb reverse`. Its `c2.goldfish.vp8.decoder` is not hardware evidence.
- The mapping parser, writer-restart behavior, torn-frame rejection, bounded audio, fresh-reader
  semantics, silence fallback, clean remote-track teardown, and aiortc tracks have deterministic
  tests.
- Godot import/build/export and local runtime pass. On the API 34 emulator, two sequential peers
  received non-black Godot frames and microphone return while the renderer remained active; stale
  retained tone PCM was not replayed on reconnect.
- All physical-device and hardware-codec criteria are deferred to Milestone 9 and remain not
  executed. Per ADR-0004, they do not block Milestones 2-8 but remain mandatory for release.

## Historical note

An initial Unity proof implemented the same mappings but could not run because no eligible editor
license was available. That source was removed when ADR-0003 selected Godot. The failed attempt is
retained only in dated benchmark records; it is not part of the current architecture.

## References

- [.NET named memory-mapped files](https://learn.microsoft.com/dotnet/api/system.io.memorymappedfiles.memorymappedfile)
- [Godot license](https://godotengine.org/license/)
- [Godot viewport documentation](https://docs.godotengine.org/en/stable/tutorials/rendering/viewports.html)
