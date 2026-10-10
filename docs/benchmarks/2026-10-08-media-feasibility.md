# 2026-10-08 media feasibility record

This is a functional-test record, not a performance benchmark. It was written under the original
milestone schedule; ADR-0004 later moved physical/performance acceptance from Milestone 1 to
Milestone 9. The statement below describes the evidence available on this date, not the current
Milestone 1 completion rule.

- Real aiortc peers negotiated generated 1280x720 video, 48 kHz application audio, and reverse
  audio in 4 passing automated tests.
- The native Android debug APK compiled against libwebrtc but was not installed or run.
- No video FPS, bitrate, startup latency, audio latency, CPU, GPU, RAM, VRAM, packet loss, codec
  selection, thermals, or stability measurements were collected.
- No physical phone or 3D renderer installation was available.

Consequently, no performance or hardware acceptance criterion passed in this run. Run
`scripts/benchmark.ps1 -Profile inventory` for machine inventory; `-Profile media-poc` correctly
refuses until a hardware measurement harness exists.
