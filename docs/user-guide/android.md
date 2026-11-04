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
6. Grant camera permission when you choose **Scan host QR**. The camera is used only by the local
   QR scanner; no image is uploaded or retained by govor.ai.

Android installation and developer-verification policy changes independently of govor.ai. Check
the current official Android guidance for the learner's device and region before distributing an
APK: <https://developer.android.com/developer-verification>.

## First pairing

1. Connect the phone over Wi-Fi to the same trusted private LAN as the Windows PC. The PC may use
   Ethernet or Wi-Fi. Guest/client-isolated Wi-Fi and unrouted VLANs prevent the required device-
   to-device path. A Windows Public profile is supported on the trusted router but may require a
   matching Windows Firewall allowance.
2. Start `Start-Govor.cmd` on Windows and leave its console open.
3. Tap **Scan host QR** and point the phone at the QR displayed over the Windows renderer. The app
   validates the version, expiry, addresses, code, and certificate fingerprint locally, then
   connects without requiring you to transcribe them.
4. If camera scanning is unavailable, expand **Pair manually** and enter:
   - **Media host:port:** the displayed PC address followed by `:8766`;
   - **Control host:port:** the same PC address followed by `:8765`;
   - **Pairing code:** the current eight-digit one-time code; and
   - **PC certificate SHA-256:** the complete fingerprint shown in the Windows console. Colons and
     spaces are optional, but all 64 hexadecimal characters must match.
5. For manual pairing, tap **Connect manually**. The lesson list comes from the Windows host.
6. On **Choose a lesson**, use the list icon to select a lesson and the settings icon to choose the
   accent and spaced-review preference, then tap **Start lesson**.
7. Confirm that both media and lesson state become connected before speaking.

The code expires after ten minutes and is consumed by the first successful exchange. The app
encrypts the resulting random device credential with Android Keystore. On later starts, tap
**Reconnect to saved host**. Use **Scan a different host QR** if the host address or identity has
changed.

## Lesson controls and microphone

From **Choose a lesson**, tap **+ Create a lesson**, or open the lesson list and choose
**Create a new lesson**. Enter a topic; difficulty, environment, and length are optional. The PC
shows creation progress too. You may lock the phone while generation runs; the app retrieves its
status after reconnecting and selects the new lesson once it is installed. Keep the Windows host
running. A failed or timed-out request shows a result you can dismiss before trying again.

- Teacher and environment audio plays through the phone's main loudspeaker by default, not the
  quiet call earpiece. Use the phone's volume buttons to adjust it. govor.ai restores the
  previous communication-audio route after disconnecting or moving to the background.
- Hold the large microphone button labelled **Hold while speaking** for the entire learner response
  and release it when finished.
- Do not start another recording while the app shows `processing` or the teacher is speaking.
- Tap the replay icon to repeat the last teacher audio locally without advancing the lesson.
- Tap the speedometer icon, then choose `0.75×`, `1×`, or `1.25×` to change teacher playback speed.
- Tap the pronunciation icon to open the word sheet. Select a word to view IPA/Bulgarian help and
  request isolated-word audio; annotated subtitle words can also be selected directly.
- Open the three-dot menu and choose **Disconnect** to end the current connection. Interrupted
  lessons retain structured progress on Windows and resume at the current exercise.
- To choose another lesson while keeping the connection, tap the toolbar Back arrow or choose
  **Leave lesson** from the three-dot menu. Android Back opens the same confirmation. Choose
  **Leave lesson** to return to selection, or **Keep learning** to continue. Completed exercises
  are saved automatically.
- To remove the lesson itself, open it, then choose **Delete lesson** from the three-dot menu.
  Check the lesson name in the confirmation before choosing **Delete lesson** again. This ends
  the lesson and removes it from the Windows host and connected lesson lists. Your learning
  history is kept. **Keep learning** or dismissing the dialog leaves the lesson untouched.
  Create another lesson first if it is the last one remaining.

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

## Local-network and release limits

Use the PC's private-network IPv4 address, not `127.0.0.1` and not the emulator-only `10.0.2.2`.
The PC may be wired while the phone remains on Wi-Fi when the router bridges or routes the two
links. Do not expose ports 8765/8766 to the public internet or forward them on a router. Release
WSS, pairing, and DTLS-SRTP are implemented, but each physical network topology still needs direct
firewall/connectivity evidence; emulator or software tests do not supply it.
