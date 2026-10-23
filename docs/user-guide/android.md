# Android installation and use

Use only the signed `govor.ai-<version>-android-release.apk` supplied with the same release as the
Windows package. The debug APK permits a cleartext development path and is not a learner build.

The signed release, secure pairing, update, and complete lesson passed first on an Android Studio
API 34 emulator and then on the documented physical realme RMX3939 over the intended private Wi-Fi.
The exact signed `0.1.11`/code 12 candidate completed Milestone 9 acceptance on 2026-10-22; the
earlier emulator evidence is not used as a substitute for any physical row.

## Install

1. Verify the APK SHA-256 against the release artifact manifest.
2. Transfer the APK to the phone over a trusted method.
3. Open it with Android's package installer. Android may ask you to permit installs from that file
   source. Grant the narrowest temporary permission and turn it off again afterward.
4. If the device, store, account type, or region blocks this distribution method, stop and use an
   Android-supported distribution route. Do not disable platform security globally.
5. Open govor.ai and grant microphone permission when the app asks in context. The app has no
   useful hold-to-talk path without that permission.

Android installation and developer-verification policy changes independently of govor.ai. Check
the current official Android guidance for the learner's device and region before distributing an
APK: <https://developer.android.com/developer-verification>.

## First pairing

1. Connect the phone and Windows PC to the same trusted private Wi-Fi/LAN. Guest/client-isolated
   networks may prevent devices from reaching one another.
2. Start `Start-Govor.cmd` on Windows and leave its console open.
3. In the release app enter:
   - **Media host:port:** the displayed PC address followed by `:8766`;
   - **Control host:port:** the same PC address followed by `:8765`;
   - **Pairing code:** the current eight-digit one-time code; and
   - **PC certificate SHA-256:** the complete fingerprint shown in the Windows console. Colons and
     spaces are optional, but all 64 hexadecimal characters must match.
4. Tap **Connect and load lessons**. The lesson list comes from the Windows host.
5. Choose a lesson, accent, and spaced-review preference, then tap **Start lesson**.
6. Confirm that both media and lesson state become connected before speaking.

The code expires after ten minutes and is consumed by the first successful exchange. The app
encrypts the resulting random device credential with Android Keystore. On later starts, enter the
same media/control addresses and leave the code/fingerprint blank to reuse that credential.

## Lesson controls and microphone

- Teacher and environment audio plays through the phone's main loudspeaker by default, not the
  quiet call earpiece. Use the phone's volume buttons to adjust it. govor.ai restores the
  previous communication-audio route after disconnecting or moving to the background.
- Hold **Hold to talk** for the entire learner response and release it when finished.
- Do not start another recording while the app shows `processing` or the teacher is speaking.
- **Replay** repeats the last teacher audio locally without advancing the lesson.
- `0.75×`, `1.0×`, and `1.25×` change teacher playback speed.
- Tap an annotated word to view pronunciation and request isolated-word audio.
- **Disconnect** ends the current connection. Interrupted lessons retain structured progress on
  Windows and resume at the current exercise.

The app does not save raw microphone recordings. Normal logs omit full learner transcripts.

## Update

Install an APK with a higher version code over the existing app. Android accepts an in-place
update only when it has the same application ID and signing key. Do not uninstall first: an
uninstall removes the Android Keystore credential and requires pairing again. Learner progress is
stored on Windows and is unaffected by an Android-only update.

## Uninstall or reset pairing

- Use Android Settings > Apps > govor.ai > Uninstall. This removes the app and its encrypted
  device credential; it does not delete Windows progress or models.
- To pair again without uninstalling, clear govor.ai storage in Android Settings, then obtain a new
  code from a restarted Windows launcher.

## Wi-Fi and release limits

Use the PC's private-network IPv4 address, not `127.0.0.1` and not the emulator-only `10.0.2.2`.
Do not expose ports 8765/8766 to the public internet or forward them on a router. Release WSS,
pairing, and DTLS-SRTP are implemented, but physical Wi-Fi/firewall behavior, phone acoustics,
hardware codecs, lifecycle recovery, and bounded stability require the recorded release evidence.
