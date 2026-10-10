# ADR-0004: Run physical target-environment acceptance in Milestone 9

- Status: accepted
- Date: 2026-10-09

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
security, target-machine performance, orientation, unfocused/monitor-off, thermal, and soak checks
are one mandatory Milestone 9 target-hardware acceptance bundle.

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
resources, unfocused/monitor-off behavior, thermals, and a 30-minute continuous lesson.
