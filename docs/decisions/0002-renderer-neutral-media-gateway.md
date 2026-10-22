# ADR-0002: Prove native WebRTC through a renderer-neutral media boundary

- Status: accepted; target-hardware release acceptance passed in Milestone 9
- Date: 2026-10-08
- Updated: 2026-10-22 after physical target-path measurement

## Context

The highest-risk integration is continuous Windows video/application audio to a native Kotlin
Android client plus microphone audio in the reverse direction. Binding the application protocol to
one engine's WebRTC package would combine renderer, signaling, codec, and Android interoperability
risk before any of them had evidence.

## Decision

Own a small versioned signaling contract and keep media transport behind a renderer-neutral local
boundary. aiortc is the Windows WebRTC peer. A renderer supplies only its latest complete
1280x720 RGBA frame and application-owned PCM through two Windows named memory mappings.

Video uses two alternating latest-frame slots. The writer fills the inactive slot and commits a
small header only after the complete RGBA frame is present; the reader verifies that header stayed
stable during its copy. The aiortc track may await the next publication for up to 20 ms when its
30 fps sample precedes Godot's publication, avoiding phase-alias repeats without building a queue.
Audio uses a bounded ring of 20 ms, 48 kHz mono blocks. Publication sequences reject torn writes,
writer-generation values permit renderer restart, and a lagging reader skips stale data rather
than growing memory. A newly attached audio reader begins after the current write position so
reconnect cannot replay a retained block after PCM production has stopped. aiortc owns pacing,
silence fallback, encoding, DTLS-SRTP, and the Android-facing peer connection.

The current renderer is Godot 4.7.2 .NET, selected in ADR-0003. Changing renderers must not alter
the Android signaling or media contracts.

The bridge is the accepted path. It performs GPU-to-CPU readback and a managed copy before aiortc
software VP8 encoding. The target run sustained the cadence and resource goals with that fallback;
Windows hardware encoding was unavailable and is recorded as such. If later target configurations
miss the release gate, first evaluate an asynchronous Godot GDExtension or a dedicated native
capture/hardware-encoding bridge.

Android libwebrtc remains pinned to `io.github.webrtc-sdk:android:150.7871.01` for this experiment,
including its BSD and third-party notices.

## Rejected

- A WebView receiver: violates the native-client requirement.
- Engine-owned signaling/WebRTC: couples the wire protocol and native client to a renderer plugin.
- Building libwebrtc from source before feasibility evidence: disproportionate checkout and build
  cost for the first gate.
- Sending raw renderer frames over a LAN socket: expands the attack surface without solving codec
  or latency requirements.

## Milestone 9 release evidence

The exact post-audit package passed the physical path, bounded stability, bilingual lesson flow,
restart, and pronunciation checks. On 2026-10-22 the learner also confirmed the moving phone
picture and teacher-audio intelligibility, closing the inherently subjective row and Milestone 9.
ADR-0004 records both that evidence and the product decision that no fixed-duration continuous
lesson or soak is required.

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
- On 2026-10-21 a realme RMX3939 on the intended Wi-Fi completed authenticated WSS/DTLS-SRTP,
  physical microphone return, lifecycle and network recovery, hardware VP8 decode, monitor-off,
  cadence/resource measurement, and a 1,800-second transport/media soak. Godot publications
  averaged 29.726 fps; video/audio packet loss was zero.
- The same run recorded the Windows side as VP8 software encoding. That fallback met the measured
  cadence target, but no Windows hardware-encoding claim is made.
- On 2026-10-22 the exact post-audit package passed a physical smoke, complete café scenario,
  restart/progress check, IPA display, and isolated-word playback. Human visual/acoustic
  confirmation remains outside automation.

## Historical note

An initial Unity proof implemented the same mappings but could not run because no eligible editor
license was available. That source was removed when ADR-0003 selected Godot. The failed attempt is
retained only in dated benchmark records; it is not part of the current architecture.

## References

- [.NET named memory-mapped files](https://learn.microsoft.com/dotnet/api/system.io.memorymappedfiles.memorymappedfile)
- [Godot license](https://godotengine.org/license/)
- [Godot viewport documentation](https://docs.godotengine.org/en/stable/tutorials/rendering/viewports.html)
