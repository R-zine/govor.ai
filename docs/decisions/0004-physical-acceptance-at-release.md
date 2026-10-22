# ADR-0004: Run physical target-environment acceptance in Milestone 9

- Status: accepted
- Date: 2026-10-09
- Updated: 2026-10-22 after target-hardware execution and bounded-stability scope decision

## Context

Milestone 1 originally combined two different decisions: proving that the renderer-neutral WebRTC
architecture works with the native Kotlin client, and certifying the final physical deployment
environment. The repository now has direct development evidence for the first decision through a
native Android Studio emulator, but no suitable physical phone is available for the second.

Blocking all teaching-system work on unavailable final hardware would prevent progress even though
the media boundary is replaceable and its highest-risk software interactions have executed. At the
same time, deleting or weakening physical acceptance would make release claims unsafe.

## Decision

Milestone 1 is complete when the native-emulator media proof and development architecture decision
pass. Physical phone, Wi-Fi, acoustic, hardware-codec, physical lifecycle, release-network
security, target-machine performance, orientation, unfocused/monitor-off, thermal, and bounded
stability checks are one mandatory Milestone 9 target-hardware acceptance bundle.

This is a scheduling change, not an evidence substitution:

- Milestones 2-8 may proceed without a physical phone.
- Emulator results remain valid only as Milestone 1 development evidence.
- No emulator, mock, loopback, compilation, or generated artifact may satisfy a Milestone 9
  physical row.
- Milestone 9 cannot complete, and no release hardware claim may be made, until the entire bundle
  executes on documented target hardware and the intended Wi-Fi/network path.
- If final measurements invalidate the current readback, codec, or transport implementation, the
  architecture must be revised before release even if that requires rework.

## Consequences

- Milestone 2 session orchestration is unblocked.
- The current Godot/aiortc/native-Android architecture is accepted for continued development.
- Hardware scripts and ledgers remain separate and continue rejecting emulator serials.
- Status and roadmap reports list absent physical evidence under Milestone 9, not as a Milestone 1
  blocker.
- Replaceable renderer/media boundaries remain important because definitive hardware evidence
  arrives late.

## Milestone 9 bundle

The authoritative checklist is in `docs/MASTER_SPEC.md` under Milestone 9. It includes physical
video/audio/microphone, independence from PC audio hardware, intended Wi-Fi, pairing/WSS/firewall,
lifecycle and network recovery, codec selection/fallback, orientation/acoustics, latency and
resources, unfocused/monitor-off behavior, thermals, and recorded bounded stability.

On 2026-10-22 the product owner removed the fixed 30-minute continuous-lesson requirement. It was
disproportionately inconvenient to supervise a phone tethered to the test PC and did not add useful
evidence beyond bounded interactive, lifecycle, performance, and teardown checks. Future agents
must not block release on a 30-minute lesson or soak. The already executed 1,800-second transport
run remains valid historical supporting evidence and must not be misrepresented as interactive.

## Current execution status

The 2026-10-21 target run used a realme RMX3939 and the target RTX 3060 Windows PC on the intended
private Wi-Fi. It directly measured physical Wi-Fi transport, phone microphone return, hardware
VP8 decode, the Windows software-encode fallback, lifecycle/network recovery, monitor-off and
unfocused rendering, resources, thermals, packet loss, and a 1,800-second media transport soak.
Those rows are now evidence, not emulator inference.

The historical transport run was not a continuously interactive learner lesson and is not labeled
as one. On 2026-10-22 the post-audit 0.1.11 candidate passed a 30-second physical smoke, complete
café flow, restart/progress survival, pronunciation inspection, and word playback. A later
unlocked-phone follow-up sent the explicit bounded Piper phrase `Какво означава order?` through
the physical microphone, received Bulgarian guidance and an English prompt, recognized following
English answers, displayed IPA/help, and advanced the same attempt to 3/3. Whisper displayed the
Bulgarian input only as `(speaking in foreign language)`, so this is bilingual-flow evidence, not
a human-speech accuracy claim. On 2026-10-22 the learner confirmed that the moving scene was
visible and teacher speech was audible, clear, and intelligible on the physical phone. That closes
the subjective row and the complete Milestone 9 bundle.
