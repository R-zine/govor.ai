# Android user guide (development status)

The Android application is not yet ready for learner use. Its debug build now provides a native
Compose WebRTC feasibility screen: enter the Windows host and development token, connect, view
remote video, hear remote application audio, and hold the microphone button to transmit. The
debug default `127.0.0.1:8766` is for an Android Studio emulator with
`adb reverse tcp:8766 tcp:8766`; a physical device uses the Windows LAN address.

An Android Studio API 34 emulator completed video/audio/microphone and reconnect development
checks on 2026-10-09. No physical-device run has occurred. Proper pairing, WSS, subtitles,
release signing, installation/update UX, physical hardware-codec evidence, and accessibility
acceptance remain to be implemented and tested. Physical-phone and Wi-Fi validation is scheduled
as part of the final Milestone 9 release-acceptance bundle.

Do not distribute the debug APK as a finished application.
