# Hardware test ledger

Milestone 9 hardware acceptance required a physical Android phone and suitable Windows
GPU/audio/network conditions and completed on 2026-10-22. Emulator and synthetic loopback results
may diagnose code but do not satisfy device criteria. ADR-0004 made this a final release gate
rather than a prerequisite for Milestones 2-8.

## 2026-10-08 environment inventory

- Windows reported by process: Windows 10.0.26200
- GPU: NVIDIA GeForce RTX 3060, 12,288 MiB
- NVIDIA driver: 560.94
- Android SDK: Platform 34, Build Tools 34.0.0 initially (35.0.0 later installed by the build),
  Platform Tools 34.0.3
- Android Studio/JDK: Android Studio 2022.2-era install, OpenJDK 17.0.6
- Renderer engine: not installed during this initial inventory
- Repository-local .NET SDK installed: 8.0.425
- Local AVD definitions: `Pixel_3a_API_34_extension_level_7_x86_64` and `Pixel_4_API_33`

### Device enumeration

Command executed with permission to start the ADB daemon:

```powershell
adb start-server
adb devices -l
```

Result: command succeeded and listed zero devices. No physical phone was connected or authorized.
The initial inventory did not launch an AVD. A separate development-only emulator run was later
performed on 2026-10-09 and is recorded below; it does not satisfy physical compatibility.

### 2026-10-08 Milestone 9 acceptance snapshot (not executed at initial inventory)

| Criterion | Result | Reason |
| --- | --- | --- |
| Physical continuous video | blocked/not executed | No physical device |
| Teacher audio on phone | blocked/not executed | No device |
| Phone microphone reaches PC | blocked/not executed | No device |
| No PC speaker/microphone dependency | blocked/not executed | Requires end-to-end device run |
| Local Wi-Fi operation | blocked/not executed | No device connection |
| Native hardware decode / Windows hardware encode | blocked/not executed | No device or measured encoder path |
| Disconnect/reconnect and state integrity | blocked/not executed | Requires physical-device execution; emulator development path passes |
| Unfocused/monitor-off renderer | blocked/not executed | No renderer runtime was available during this 2026-10-08 run |
| Performance and latency measurements | not executed | No suitable end-to-end path |
| Bounded stability | not executed | No suitable end-to-end path |

The aiortc in-process loopback tests are recorded in `docs/milestones/STATUS.md`; they are software
tests, not hardware acceptance.

## 2026-10-09 Android Studio emulator development run

The `Pixel_3a_API_34_extension_level_7_x86_64` AVD booted and enumerated as `emulator-5554` with
model `sdk_gphone64_x86_64`. The current debug APK was installed and connected through
`adb reverse tcp:8766 tcp:8766` to the loopback media server.

Native VP8 video render, remote audio playout startup, reverse 48 kHz microphone frames, and a
disconnect/reconnect cycle were observed. The virtual decoder identified itself as
`c2.goldfish.vp8.decoder`; this is explicitly not evidence of hardware decoding. The detailed
record and screenshot are in `docs/benchmarks/2026-10-09-android-emulator-media.md`.

At this checkpoint all physical-device rows above remained unexecuted. The emulator also does not
establish Wi-Fi behavior, acoustic audio quality, physical microphone behavior, encoder/decoder
hardware selection, performance, thermals, or stability. The physical rows later passed in the
2026-10-21/22 Milestone 9 run recorded below.

The hardware-test script explicitly filters out ADB serials beginning with `emulator-` and returns
the blocked exit code when no physical serial remains.

## 2026-10-09 superseded Unity bridge attempt

This is a historical failure record. ADR-0003 replaced Unity with Godot 4.7.2 .NET, all Unity
source and active build paths were removed, and no command below is a current project command.

The renderer now contains a Windows-local shared-memory publisher for its 1280x720 RGBA capture
surface and application-owned 48 kHz mono PCM. The aiortc service has a matching renderer source,
with deterministic tests for torn publications, bounded audio order, writer restart, frame
conversion, silence fallback, signaling, and existing bidirectional WebRTC behavior.

This entry is source/software evidence only:

- `./scripts/test.ps1 -Scope media`: passed, strict mypy and 9 tests.
- Renderer named-mapping open/close smoke: passed in Python on Windows.
- `./scripts/test.ps1 -Scope unity`: runtime C# source compilation passed against the exact
  2022.3.62f1 assemblies; editor tests remained blocked because Unity produced no XML,
  LicensingClient IPC timed out after 60 seconds, and Unity returned 199.
- Unity player build, scene launch, visual inspection, two-second audible check, GPU readback,
  shared-memory publication, aiortc consumption, and Android-emulator reception: not executed.
- Physical Android, Wi-Fi, codecs, latency/resources, unfocused/monitor-off behavior, and bounded stability:
  still blocked/not executed.

No hardware acceptance row changes status. Compilation and in-memory test fixtures do not prove a
physical GPU, audio device, codec, network, or Android phone behavior.

Add dated entries with device model, Android version, transport, Wi-Fi details, Windows build,
driver, commit, commands, logs, measurements, and pass/fail/block status.

## 2026-10-09 Godot migration

Godot is now the only active renderer. Checksum-pinned bootstrap, headless import/build/self-test,
Windows export, local runtime, changing non-black shared-memory frames, and non-silent PCM all
passed. A supervised audible check stopped automatically after two seconds.

`./scripts/emulator-renderer-smoke.ps1` passed on the API 34 AVD through `adb reverse`. The aiortc
peer received non-black 1280x720 Godot RGBA (`rgb_max=255`) and 48 kHz PCM (`peak=2621`), Android
libwebrtc reported its first rendered frame and a 1280x720 resolution change, and Windows received
a 48 kHz/960-sample emulator microphone frame. A later callback interval reported 120 frames
rendered with zero drops over 4.001 seconds (30.0 fps). Disconnect/reconnect then passed with a second
non-black Godot frame and second microphone return; teardown was clean and stale tone PCM was not
replayed. The bounded script stopped the Android app, renderer, server, and reverse mapping.

The ADB screenshot captured the connected UI but a black WebRTC `SurfaceView`. Because non-black
pixels reached aiortc and Android emitted render callbacks, the screenshot is recorded as
inconclusive rather than as visible-scene proof. Controlled performance/latency,
unfocused/monitor-off behavior, and bounded stability were not executed; the short emulator interval is not a
physical performance result.

Exact commands, artifacts, failures, and limitations are in
`docs/benchmarks/2026-10-09-godot-renderer-migration.md`. At this checkpoint every physical-device
acceptance row was still unexecuted; those rows later passed in Milestone 9 and do not alter the
scope of the completed Milestone 1 proof.

## 2026-10-10 Milestone 2 emulator session run

`./scripts/emulator-renderer-smoke.ps1` passed again after adding the complete deterministic
session-control path. Through debug-only `adb reverse` on ports 8765 and 8766, the API 34 emulator
played the initial bounded teacher WAV, reported playback completion, entered hold-to-talk,
returned WebRTC microphone frames, displayed the scripted fake STT transcript and next fake
teacher response, then repeated the media/control setup after disconnect/reconnect. Godot
acknowledged every allow-listed renderer action. Cleanup removed the Android app process, Godot,
both Python servers, both reverse mappings, and all listening ports.

The final run reported 120 received/rendered frames with zero drops over 4.002 seconds (30.0 fps),
and wrote a completed-turn UI hierarchy artifact in addition to the connected screenshot. These
figures describe only a short emulator loopback diagnostic and are not target performance data.

This is native-emulator functional evidence for Milestone 2 only. The fake recognizer did not
transcribe microphone samples, and the virtual device supplies no physical acoustics, Wi-Fi,
hardware-codec, thermals, or target-lifecycle evidence. At this checkpoint every Milestone 9 row
was still unexecuted; those rows later passed independently. Exact commands, transient failures,
artifacts, and limitations are recorded in
`docs/benchmarks/2026-10-10-milestone-2-session-orchestration.md`.

## 2026-10-11 Milestone 3 desktop local-AI run

`./scripts/benchmark.ps1 -Profile local-ai` passed on the Windows development PC. This compared two
Qwen3 quantized models, ran real llama.cpp and whisper.cpp processes, transcribed English and
Bulgarian human-speech files, and exercised two local-provider turns through host orchestration.
The selected 4B model and recognizer results are recorded in
`docs/benchmarks/2026-10-11-local-ai-bilingual.md`.

This did not use a physical phone or the intended Wi-Fi/acoustic path. The recordings are local
fixtures, the host smoke injects them at the microphone-source boundary, and response audio is a
diagnostic marker rather than TTS. It changes no Milestone 9 row: phone microphones, speakers,
Wi-Fi, codecs, concurrent target load, latency, thermals, lifecycle, and bounded stability remain not executed.

## 2026-10-12 Milestone 4 speech emulator run

`./scripts/emulator-speech-smoke.ps1` passed on the API 34 AVD through debug-only `adb reverse`.
The native Android client decoded and played the real Kokoro `en-GB` PCM16 WAV, advanced all seven
word highlights using model-reported media timestamps, completed a 0.75× replay without advancing
the host lesson twice, selected the first word, and completed a separately synthesized word WAV.
The ignored evidence files are `.cache/speech-emulator-android.log`,
`.cache/speech-emulator-lesson.xml`, and `.cache/speech-emulator-window.xml`.

The smoke used generated diagnostic WebRTC media only to keep the existing Android connection
surface active; the teacher voice itself came from Kokoro over the bounded control contract. Its
`finally` path force-stopped the app, control server, media server, and reverse mappings. Ports
8765/8766 and Android playback were checked inactive afterward, so no tone or speech remained.

This proves native-emulator decoding, scheduling, interaction, and cleanup. It does not prove a
physical speaker, phone, acoustics, Wi-Fi, hardware codec, target performance, or speech
naturalness. At this checkpoint those target-hardware rows remained unexecuted; they later passed
independently in Milestone 9.

## 2026-10-12 Milestone 6 scene/avatar emulator run

`./scripts/emulator-speech-smoke.ps1` launched the exported Godot renderer alongside real Kokoro
and the API 34 emulator. The host selected the café scene from lesson context; Godot acknowledged
the validated scene and logged 51 PCM energy samples plus 23 real provider-aligned viseme cues for
the 2,038,666 µs teacher utterance. Android completed the synchronized speech interactions. The
script force-stopped the app, renderer, servers, and reverse mappings afterward.

`./scripts/emulator-renderer-smoke.ps1` separately required the lesson-context café marker and a
fake-provider animation containing nonempty PCM energy but zero visemes/source `none`. It preserved
the existing Godot-to-aiortc video, Android render, microphone-return, and reconnect checks. This
proves the missing-alignment fallback does not invent timing or block animation.

The four-environment scene tour and concurrent Qwen performance run happened on the Windows
development PC, not on the Android emulator; details are in
`docs/benchmarks/2026-10-12-avatar-scenes-and-renderer-performance.md`. No physical-device row
changed status in this emulator run. Physical codec/fallback, intended Wi-Fi, acoustics, target
performance, lifecycle, thermals, monitor-off, and bounded stability later passed independently in
Milestone 9.

## 2026-10-15 Milestone 8 signed-release emulator run

The signed `0.1.1` release APK (`versionCode=2`) updated the installed signed `0.1.0` APK
(`versionCode=1`) without uninstalling it. Android retained the original installation timestamp,
the encrypted Android Keystore gateway credential continued to authenticate, and the protected
Windows progress database had the same SHA-256 immediately before and after the binary update.

The API 34 emulator connected to the packaged Windows launcher through its normal virtual-router
address `10.0.2.2` over certificate-pinned HTTPS/WSS. No `adb reverse`, debug token, cleartext
manifest, or development host process was used in the application path. The media service logged
non-black 1280x720 renderer frames and 48 kHz/960-sample client microphone frames.

After restarting the AVD with its explicit host-audio switch, two bounded acoustic PC-playback
turns advanced the release lesson. The final deterministic turn used the installed emulator's
loopback `android.emulation.control.EmulatorController/injectAudio` interface while the signed app's
real hold-to-talk control was held. Whisper returned “Here, please. I will have my coffee for here,
please.” The UI then displayed `Lesson complete · progress saved`; the SQLite view showed café
`completed_count=1`, exercise index 3, and three successful exercises. This is a deterministic
emulator-input technique, not a phone microphone or acoustic test.

Stopping the launcher closed all managed children. The app and emulator were stopped immediately;
ports 8765–8768 had zero listeners and no package-owned process remained. No audio continued.
Exact commands, package hashes, transient failures, and limits are in
`docs/benchmarks/2026-10-15-release-packaging-and-distribution.md`.

This run changes no Milestone 9 row. It used a virtual router rather than the intended Wi-Fi, a
virtual microphone injection rather than physical acoustics, and an emulator codec rather than
phone hardware. Physical installation, Android platform verification, Windows Firewall behavior,
credential storage, video/audio/microphone behavior, lifecycle, codecs, performance, thermals,
monitor-off behavior, and bounded stability all remain not executed on target hardware.

## 2026-10-17 Milestone 8 local clean-VM fixture

This is the historical pre-execution record. The clean-software run later passed on 2026-10-19 as
recorded in the next section; none of the Milestone 9 hardware rows changed.

A QEMU 11.0.50/WHPX fixture is implemented for the one remaining Milestone 8 software row. It uses
an official, caller-supplied, digest-verified Windows 11 Enterprise evaluation ISO; a stopped clean
base; a disposable qcow2 run overlay; generated-key loopback SSH; and host-loopback forwarding.
The host Android emulator reaches guest release ports through `10.0.2.2:18765/18766`, without a
nested emulator or `adb reverse`.

Host QEMU/WHPX, EDK2 pflash, quoted-path, and qcow2-disk startup passed a bounded process probe. The
official ISO is absent, so no guest was provisioned and no Windows setup, Godot launch, emulator
connection, or guest teardown was executed. This is **blocked**, not hardware evidence and not a
clean-Windows pass. Exact implementation evidence is in
`docs/benchmarks/2026-10-17-m8-local-vm-fixture.md`; the runbook is
`docs/testing/m8-clean-vm.md`.

The later passing VM run leaves every Milestone 9 row unchanged: the VM is not the target
Windows machine, and the Android Studio emulator is not a physical phone. Intended Wi-Fi,
physical acoustics, hardware codecs, lifecycle, latency/resources, monitor-off behavior, thermals,
and bounded stability are still not executed.

## 2026-10-19 Milestone 8 clean-VM and host-emulator acceptance

This entry closes only Milestone 8's clean-Windows software row. It is intentionally recorded in
the hardware ledger so no future reader mistakes the VM/emulator run for target-hardware evidence.

- Host: Windows process build 10.0.26200, QEMU 11.0.50 with WHPX.
- Guest: `GOVOR-M8-VM`, Windows 10.0.22000.0 AMD64, 8 GiB RAM/four virtual CPUs.
- Test image: user-supplied, 4,693,557,248 bytes, SHA-256
  `15fecff356411d43c77df040e1847427402b0e09da069bf1db0cb754932075b9`; not distributed, with
  provenance/activation/licensing not independently verified.
- Android: host API 34 AVD `emulator-5554`, `sdk_gphone64_x86_64`; release APK 0.1.4/code 5.
- Network: QEMU user networking with host-loopback TCP 18765/18766 and UDP 18770; Android used
  `10.0.2.2`; `adb reverse --list` was empty.

The final 0.1.4 ZIP was independently re-hashed in the guest. `Setup-Govor.cmd` verified the
conditional Microsoft VC++ prerequisite and all six pinned models. `Start-Govor.cmd` launched the
actual local providers and Godot renderer. Authenticated WSS/DTLS-SRTP connected; the guest media
log recorded non-black 1280x720 Godot video (`rgb_max=255`), nonzero 48 kHz/960-sample Godot PCM
(`peak=2621`), and a 48 kHz/960-sample emulator microphone frame. Android logged the 1280x720
goldfish VP8 decoder, rendered frames, audio playout, and an active microphone recorder. The exact
Retry lesson action recovered a transient lesson error in one run.

The final bounded shutdown record reported task `Ready`, zero listeners, zero owned processes, and
`clean_shutdown=true`. The emulator was killed and the VM shut down normally; no server or tone
remained. ADB `SurfaceView` screenshots were intermittently black despite non-black media and
Android render callbacks, so they are not visible-scene evidence.

This run does not change any Milestone 9 row. The physical phone, intended Wi-Fi, physical
speakers/microphone, acoustic path, hardware codecs, lifecycle/interruption, target performance,
monitor-off behavior, thermals, and bounded stability remain not executed. Exact commands, artifact
hashes, failures, and limits are in
`docs/benchmarks/2026-10-19-m8-clean-vm-acceptance.md`.

## 2026-10-21 Milestone 9 physical target run

Configuration:

- Target PC: Windows process build 10.0.26200; NVIDIA GeForce RTX 3060 12,288 MiB; driver 560.94.
- Physical phone: realme RMX3939, Android 16/API 36, 720x1600 at density 320, security patch
  2026-08-01. The ADB serial is intentionally not recorded.
- Network: SSID `A1_B436`, WPA2-Personal, 2.4 GHz channel 7/802.11ax. PC
  `192.168.100.61/24`, phone `192.168.100.71/24`; the Windows profile was verified Private.
- There was no `adb reverse` mapping. The phone used the LAN-facing release HTTPS/WSS gateways.
- Measured candidate: `0.1.10`/code 11 signed APK, 55,425,173 bytes, SHA-256
  `2bbfb230925767f50613c0947702241103556ccb93c1840d97f495b524c2d50d`. The signer is the
  existing RSA-3072 release identity; no signing secret is recorded.

Executed commands included:

```powershell
./scripts/package.ps1 -Version 0.1.10 -VersionCode 11 -NoArchive `
    -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
./scripts/hardware-test.ps1 -DurationSeconds 30 -SampleIntervalSeconds 5 `
    -OutputPath .cache/m9-final-candidate-smoke.json
./scripts/hardware-test.ps1 -DurationSeconds 1800 -SampleIntervalSeconds 5 `
    -OutputPath .cache/m9-physical-soak.json
```

The wrapper verified exactly one non-emulator device, Wi-Fi addressing, no reverse mapping, the
signed running package, release media listener, authenticated connected metrics, renderer
publication, and physical microphone frames before delegating to the benchmark. Its original
array-splat implementation passed `-Profile` as a literal positional value; hashtable splatting
fixed that harness defect before the recorded runs.

| Criterion | Result | Direct evidence and limit |
| --- | --- | --- |
| Physical intended-Wi-Fi path | verified passing | Release HTTPS/WSS and WebRTC used the documented LAN addresses with no reverse mapping; all 292 soak pings succeeded |
| Pairing/authentication/secure media | verified passing | First pairing and later Android-Keystore credential reuse passed; WSS authenticated and metrics reported connected DTLS-SRTP |
| Continuous renderer transport | verified passing | 1,800.065 seconds; 54,035 emitted frames (30.018 fps), 53,508 unique Godot frames (29.726 fps); p50/p95 publication intervals 33.333/33.349 ms, max 133.335 ms |
| Physical phone microphone reaches PC | verified passing | 89,863 additional 48 kHz microphone frames during soak; earlier supervised hold-to-talk turns reached recognition and advanced café to 2/3 |
| Teacher audio from phone | verified passing | Phone lesson state advanced through playback with Windows playback muted; on 2026-10-22 the learner confirmed handset teacher speech was audible, clear, and intelligible |
| No PC audio-hardware dependency | verified architecturally/partially physically | Muting the default Windows playback endpoint did not stop phone playback completion/lesson advance; the capture service received only the phone WebRTC track and opens no PC microphone. A separate physical PC-microphone-disable action was not performed |
| Codecs | verified with fallback | Android resource-manager evidence named hardware `c2.unisoc.vp8.decoder`; RTP codec was VP8; metrics explicitly reported `windows_hardware_video_encoding=false`, so Windows used software encoding |
| Lifecycle and recovery | verified passing | Background/foreground, explicit disconnect/reconnect, and physical Wi-Fi loss/recovery reconnected without re-pairing and preserved café 2/3; ICE transition after Wi-Fi loss was delayed but recovered |
| Orientation | verified passing with product constraint | Physical attempts retained the manifest-locked portrait orientation; device rotation settings were restored afterward |
| Unfocused/monitor-off/idle-awake | verified passing | Renderer had no foreground window requirement; the monitor was turned off during the soak and video, unique renderer frames, microphone frames, and DTLS continued advancing. A bounded `SendMessageTimeout` was needed after an unbounded helper encountered an unresponsive window |
| Latency and loss | verified passing | 145,989 video packets and 97,775 audio packets received with zero reported loss; final RTT 13.247 ms video and 8.985 ms audio; Wi-Fi ping p50/p95/max 3/12/44 ms |
| Resources and thermals | verified passing | Windows CPU p50/p95 4.168/4.595%; RAM start/end/max 3,560,075,264/3,625,168,896/3,628,318,720 bytes; Android PSS start/end/max 123,086/120,787/123,086 KiB; VRAM start/end/max 5,116/4,632/5,296 MiB; GPU utilization p50/p95 20/44%; GPU max 62 °C; phone max 27.9 °C |
| Bounded stability | verified passing | The final exact-candidate 30-second run had advancing media/microphone counters, zero reported RTP loss, and bounded resources. A historical 1,800-second transport run supplies additional evidence but is not a release requirement or an interactive-lesson claim |
| Exact post-audit package | verified passing with recorded recognition limit | Signed 0.1.11/code 12 passed the physical Wi-Fi benchmark, café completion, clean package restart, progress survival, IPA display, isolated-word playback, and an explicit Bulgarian-help/English-return physical microphone path on 2026-10-22. Whisper displayed `(speaking in foreign language)` instead of preserving the Bulgarian phrase, so this is not a human-speech accuracy claim |
| Human visible-video/acoustic quality | verified passing | On 2026-10-22 the learner confirmed that the moving café/teacher was visible and teacher speech was audible, clear, and intelligible at the handset |

The Android lifecycle implementation now retains the last connection request in its Activity-owned
ViewModel, suppresses reconnect after an explicit disconnect, reconnects on foreground/network
availability, and blanks the one-time pairing token before release retries. Four pure Kotlin policy
tests cover those decisions. The media service exposes authenticated-session statistics only at a
loopback-only internal endpoint; no LAN metrics route was added.

The monitor-off helper's original broadcast `SendMessage` blocked on an unresponsive window. It
was stopped and the display was restored with bounded `SendMessageTimeout`; the media run itself
continued. One Android relaunch attempt explicitly started a second Activity instance and appeared
disconnected. Pressing Back returned to the original connected Activity, showing that this was a
harness misuse rather than lifecycle recovery evidence. Neither failed attempt is reported as a
passing product result.

After the run, the dependency audit found `PYSEC-2026-4320` in `certifi==2026.7.22` and
`GHSA-vxj4-q4g9-crj7` in `virtualenv==21.14.6`. The lock was updated to certifi 2026.10.19 and
virtualenv 21.14.12; the repeat audit reported no known vulnerabilities. The resulting signed
`0.1.11`/code 12 APK is 55,425,173 bytes with SHA-256
`94662d516bfff260b3276522142bb7ce34a995f03400011df914940c10b87e2a`. Packaging, signing,
imports, prerequisites, and wrapper doctor smokes passed. After the phone was unlocked, the exact
candidate passed a 30.609-second physical Wi-Fi benchmark with 30.482 emitted fps, 29.959 unique
Godot fps, +1,532 microphone frames, zero reported RTP loss, connected DTLS, hardware Android VP8
decode, and the explicit Windows software-encode fallback. It then completed the café path through
physical microphone input, entered Bulgarian help after recognition ambiguity, returned to
English, saved progress, survived a clean package restart, displayed
`Welcome /wˈɛlkʌm/` with Bulgarian help, and played bounded 24 kHz isolated-word audio. No PIN was
requested, guessed, or recorded.

A later unlocked-phone attempt submitted a bounded local Piper utterance saying
`Какво означава order?` through hold-to-talk and the physical phone microphone. A repeated first
attempt was mis-transcribed as Korean text. The clean single attempt was displayed as
`(speaking in foreign language)`; the teacher nevertheless supplied Bulgarian guidance and
returned to the English prompt `Say: I would like a coffee, please.` A bounded local Kokoro answer
was recognized as `Would you like a coffee, please?`, advanced the same attempt to 2/3, and tapping
`Would` displayed `/wˈʊd/` plus Bulgarian pronunciation help. A second recognized answer,
`That's all, thank you`, advanced to 3/3. This supplies the explicit bilingual physical flow with
the transcript limitation recorded; it is not claimed as human-speech recognition evidence.

Transient recoverable lesson states passed **Retry lesson**. One Windows SAPI playback job failed
to initialize and supplied no speech, so it is not evidence. The app and release stack were then
stopped, every temporary utterance was deleted, stay-awake/rotation were restored, and ports
8765-8768 plus Godot/llama/app process checks were empty. The learner then confirmed the moving
phone scene and clear, intelligible handset speech, closing the final subjective row.

On 2026-10-22 the product owner removed the fixed 30-minute lesson/soak gate. Future acceptance
uses recorded bounded interactive, stability, lifecycle, and teardown checks. The earlier
1,800-second transport record remains historical supporting evidence only.

The app was force-stopped, phone stay-awake and rotation settings were restored, and all release
listeners, Godot, llama.cpp, and package-owned processes were stopped. No tone or media service was
left running. Detailed measurements and the completed release acceptance are in
`docs/benchmarks/2026-10-21-m9-physical-release-acceptance.md`.

## 2026-10-25 mixed Ethernet/Wi-Fi maintenance check

- Windows machine: the documented development PC, Windows build 10.0.26200.
- Intended topology: physical `Ethernet 3` host link, Android phone over the access point's Wi-Fi.
- Adapter inventory: `Ethernet 3` at `192.168.100.72/24`, Realtek PCIe GbE Family Controller,
  active physical adapter with gateway `192.168.100.1`; disconnected `Wi-Fi 4` and virtual
  adapters were also present.
- Windows profile: **Public** on the active Ethernet link at the time of the check.

The new release selector executed against the real Windows inventory and rejected the active
Ethernet address because its network category was Public. It also rejected the disconnected Wi-Fi
and virtual/link-local candidates. This is verified fail-closed behavior, not mixed-topology media
acceptance. The application did not change the machine's network category or firewall policy.

### 2026-10-26 profile-category correction

The product owner clarified that `Ethernet 3` is the intended RFC1918 LAN behind the same router as
the phone Wi-Fi. Windows' Public label describes firewall/discovery defaults, not internet address
scope. The amended selector now chooses `192.168.100.72`, reports `Ethernet 3` / Public, and emits
the trusted-router, profile-matched firewall, and no-port-forwarding warning. It still rejects the
disconnected Wi-Fi and virtual/link-local adapters. The application did not modify the Windows
profile or firewall.

| Criterion | Result | Direct evidence and limit |
| --- | --- | --- |
| Deterministic physical-adapter selection | verified passing in software | Windows inventory plus unit tests select the lowest eligible default-route metric |
| Public local-profile handling | verified passing in software | Real Public-category `192.168.100.72` Ethernet is selected with the warning marker; Private remains preferred in tests |
| Unidentified/virtual/disconnected exclusion | verified passing | Disconnected/virtual adapters remain refused; unidentified profiles fail closed |
| TCP 8765/8766 from phone Wi-Fi to host Ethernet | blocked/not executed | `adb devices -l` found no attached physical phone or emulator on 2026-10-26 |
| Authenticated WSS and QR pairing over mixed path | blocked/not executed | No LAN listener or pairing artifact was started because no phone was available for the bounded check |
| WebRTC video/audio and phone microphone return | blocked/not executed | Requires the same real mixed path with the phone attached; the Public Windows category is no longer a blocker |
| Router bridge/client isolation/VLAN behavior | not executed | Router configuration was not changed or inferred |

The signed `0.1.17`/code-18 portable candidate passed release packaging, and its embedded launcher
selected `192.168.100.72 Ethernet 3 Public` with the warning path active. The companion APK is
59,891,893 bytes with SHA-256
`cd7ac297a79871b5c75564168265b0b0e574a6ad12494968335ec659b77bb478`.

To execute the remaining check, attach the physical Wi-Fi phone, permit the packaged runtime in
Windows Firewall for this trusted router's selected profile/local network, start the exact
candidate, scan its new QR, and verify TCP/WSS plus bidirectional WebRTC media. Do not configure
router port forwarding. Record the phone, router/SSID, exact package, commands, metrics, and
cleanup in a new dated entry.

## 2026-11-03 semantic-answer text regression

The Windows 10.0.26200.0 x64 development PC/RTX 3060 ran pinned loopback llama.cpp b11540 and
Qwen3 4B Q4_K_M at 21:24:19–21:24:27 UTC. `scripts/local_ai_benchmark.py --dialogue-only` passed
28/28 semantic answer cases through the actual teaching engine and 7/7 existing bilingual cases.
Median adapter times were 1,062.2 ms and 921.4 ms respectively. No phone, microphone, recognition,
TTS, LAN, or subjective listening check was executed. No server/player remained active afterward.
Exact commands, model digest, failed attempts, ignored raw report paths, and limits are in
`docs/benchmarks/2026-11-03-semantic-answer-assessment.md`. This does not replace any physical
acceptance row or install the source fix into the currently deployed 0.1.22 host.
