# 2026-10-09 Android emulator media feasibility record

This is development evidence from an Android Studio emulator. It is not a hardware benchmark and
does not satisfy the Milestone 9 physical-device acceptance criteria in `MASTER_SPEC.md`.

## Environment and path

- Windows process build: 10.0.26200.
- AVD: `Pixel_3a_API_34_extension_level_7_x86_64`.
- Guest: API 34, model property `sdk_gphone64_x86_64`.
- Android application: native Kotlin/Compose and libwebrtc; no WebView.
- Windows peer: aiortc with generated 1280x720 video and application-owned 48 kHz tone.
- Transport: `adb reverse tcp:8766 tcp:8766` to a loopback-bound server. This did not exercise
  Wi-Fi, LAN routing, firewall configuration, or release pairing.

The debug APK was installed with `adb install -r`; the app connected to `127.0.0.1:8766`. The
development token used for the run is intentionally not recorded.

## Observations

| Check | Emulator result | Limit |
| --- | --- | --- |
| Native signaling and negotiation | passed | Non-trickle offer/answer completed after changing ICE to `GATHER_ONCE` |
| Video reception | passed | Moving 1280x720 diagnostic video rendered in the native `SurfaceViewRenderer` |
| Decoder | `c2.goldfish.vp8.decoder`, VP8 | Emulator software/virtual codec; not physical Android hardware decode |
| Render cadence | mostly 29.9-30.4 fps, zero drops in several log intervals | Other automation intervals were about 24-26 fps; not a controlled benchmark |
| Remote audio playout | playout thread started | Emulator output reported 8 kHz; source was 48 kHz, and no objective acoustic measurement was made |
| Hold-to-talk microphone | passed | PC received its first client frame at 48 kHz with 960 samples |
| Disconnect/reconnect | passed | Automated UI cycle returned to `connected` |

The connected UI and moving frame are captured in
[`local/2026-10-09-emulator-connected.jpg`](local/2026-10-09-emulator-connected.jpg).

The PC logged only microphone metadata for the first frame. It did not log audio samples, the
token, or a transcript. The media server was stopped immediately after the check, and port 8766
was verified closed so the diagnostic tone would not continue playing through the emulator.

## Bugs found and corrected

1. Continuous ICE gathering could never reach the `COMPLETE` state expected by the current
   non-trickle signaling path. The client now uses `GATHER_ONCE` until trickle ICE is implemented.
2. An invalid host string could throw from OkHttp URL construction. It is now converted into a
   user-visible validation error and a clean disconnect.
3. The emulator development default is now `127.0.0.1:8766`, which works with `adb reverse`.
   Physical-device development still requires the Windows LAN address.

## Not executed

- Physical phone or tablet.
- Local Wi-Fi transport.
- Physical speaker/microphone behavior.
- Android hardware decoder or Windows hardware encoder validation.
- End-to-end latency, resource, packet-loss, thermal, or 30-minute stability measurement.
- Engine-rendered frames; this run used the clearly identified Python diagnostic source.
