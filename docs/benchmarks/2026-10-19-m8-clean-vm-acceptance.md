# Milestone 8 clean-Windows VM acceptance

- Date: 2026-10-19
- Time zone: Europe/Kyiv (UTC+03:00)
- Scope: Milestone 8 clean-Windows software and signed host-emulator release path
- Result: **passed with exact-image, VM, and Android-emulator limits**
- Milestone 9 physical-hardware effect: none

## Evidence boundary

This run may satisfy only the clean-Windows software row of Milestone 8. QEMU is not the target
Windows machine, and the Android Studio AVD is not a physical phone. The run does not establish
intended Wi-Fi behavior, physical speakers/microphone, acoustics, hardware codecs, target-machine
performance, lifecycle/interruption, unfocused/monitor-off behavior, or thermals. Those physical
rows later passed independently in Milestone 9. The product owner also removed the fixed-duration
soak requirement; neither later result changes this VM/emulator evidence boundary.

The Windows image was supplied by the user at:

```text
D:\Windows 11 Pro English x64 BiT Activated\Windows 11 Pro English x64 BiT Activated.iso
```

It was 4,693,557,248 bytes with SHA-256
`15fecff356411d43c77df040e1847427402b0e09da069bf1db0cb754932075b9`. The fixture verified that
exact digest before provisioning. The project did not download or redistribute the image and did
not independently verify its provenance, activation, or license. The result applies only to this
recorded image and guest state.

## Environment

- Development host: Windows process build 10.0.26200.
- Hypervisor: QEMU 11.0.50 (`v11.0.0-12631-g54e84cdc7a`) with WHPX, q35, EDK2 pflash, 8 GiB
  guest RAM, four virtual CPUs, and a 96 GiB sparse qcow2 disk.
- Guest: `GOVOR-M8-VM`, Windows 10.0.22000.0 AMD64.
- Android: host AVD `Pixel_3a_API_34_extension_level_7_x86_64`, serial `emulator-5554`, model
  `sdk_gphone64_x86_64`.
- Network: QEMU user mode; host-loopback SSH 55222, control TCP 18765, media TCP 18766, and fixture
  ICE UDP 18770. Android used the host alias `10.0.2.2`. `adb reverse --list` was empty.
- Guest application state: no development checkout, developer Python, Godot editor, Gradle,
  Android SDK, prior govor.ai installation, or model set existed in the clean base.

Windows Update was allowed once after provisioning. A guest reboot sometimes made QEMU/WHPX exit
with virtual-processor exit code 4; restarting the retained guest resumed safely. This is a fixture
limitation, not application evidence.

## Final artifacts

The final candidate was built with:

```powershell
./scripts/package.ps1 -Version 0.1.4 -VersionCode 5 `
  -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
```

Packaging passed Godot export, Android release build, APK signature verification, embedded Python
and hash-locked dependency staging, imports, prerequisite/doctor checks, both packaged command
wrappers, source/notices, and archive creation.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `govor.ai-0.1.4-windows-x64.zip` | 310,942,015 | `74899c85222faf65681e9512eafaee5c2dc05e79daf06d338148255ae801b838` |
| `govor.ai-0.1.4-android-release.apk` | 55,425,169 | `78799b5f943fe0caba08e9cada443ba40e42c8a4e6f1424b7c081129ebd43358` |

The APK verified with v2 signing, one RSA-3072 signer, and certificate SHA-256
`b7022cb8bbcc0a4828cf73e5ef958e1b431ccce697020577c4a502a66ec59843`. Android reported version
name 0.1.4, version code 5, min SDK 26, and target SDK 34. `adb install -r` retained the original
first-install timestamp (`2026-10-14 21:59:11`) and existing encrypted device credential.

## Clean-guest setup

The exact candidate was transferred and exercised with:

```powershell
./scripts/m8-vm.ps1 -Action Start
./scripts/m8-vm.ps1 -Action StageRelease -Version 0.1.4
./scripts/m8-vm.ps1 -Action SetupRelease -Version 0.1.4
```

`StageRelease` independently verified the ZIP and APK hashes inside the guest before extraction.
The exact packaged `Setup-Govor.cmd` reported:

- package prerequisites ready;
- Microsoft Visual C++ runtime ready; and
- all six Qwen/Whisper/Kokoro/Piper model and voice artifacts ready.

The original clean guest did not have the runtime required by packaged llama.cpp. The setup helper
now downloads Microsoft's x64 redistributable only after the runtime probe fails, then requires
size 18,731,856 bytes, version 14.51.36247.0, SHA-256
`843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c`, and a valid Microsoft
Authenticode signature before installation. The missing-runtime branch and the later already-ready
branch both passed. No arbitrary DLL was copied into the bundle.

The guest's Qwen/llama cold start took about 35.4 seconds. The release health limit was increased
to 180 seconds so a valid clean-machine cold start is not misclassified as failure.

## Release, Android, and media

The final bounded run used:

```powershell
./scripts/m8-vm.ps1 -Action StartRelease -Version 0.1.4 -SmokeSeconds 300
```

The Android release used media `10.0.2.2:18766` and control `10.0.2.2:18765`. Its existing
credential authenticated both WSS paths without entering another pairing code. QEMU user
networking made the guest's ordinary ICE host candidate unreachable from the host AVD, so the M8
harness enabled an explicit candidate `10.0.2.2:18770` backed by a host-loopback UDP forward. The
override accepts only private/loopback addresses and valid ports, is inactive outside the fixture,
and does not weaken WSS or WebRTC DTLS-SRTP.

The successful counting interval recorded:

```text
Media gateway authentication accepted
VM fixture ICE candidate prepared: host=10.0.2.2 port=18770
WebRTC connection state changed: connected
Received first renderer video frame: width=1280 height=720 rgb_min=0 rgb_max=255
Received first client microphone frame: sample_rate_hz=48000 samples=960
Received first renderer audio block: sample_rate_hz=48000 samples=960 peak=2621
```

Android libwebrtc selected `c2.goldfish.vp8.decoder`, reported a 1280x720 format and rendered
frames without drops in the sampled intervals. Audio playout started, and `AudioRecord` reported an
active 8 kHz mono voice-communication capture which WebRTC delivered to the guest as 48 kHz/960-
sample frames. The virtual goldfish decoder is not physical hardware-decoder evidence.

Normal packaged startup passes `--no-startup-tone`. For this VM check only, the harness set a
90-second fixture delay and local mute, after which Godot published its existing exact two-second
application-owned PCM signal. The delay allowed ICE to finish; no PC speaker output was enabled and
no flat tone was left running. A host isolation probe of the same final renderer binary also
observed five PCM blocks at peak 2621 plus 30 distinct non-black video frames.

The control path sometimes entered a recoverable provider error under the resource-heavy guest.
The actual **Retry lesson** action restored `lesson: ready`. During the counting run, a later media
disconnect coincided with concurrent SSH evidence copying after video/audio/microphone proof had
already been captured. An earlier run of the same exact package retained
`media: connected · lesson: ready`. This transient is recorded rather than hidden.

ADB screenshots intermittently captured the WebRTC `SurfaceView` as black. They are not used as
visible-video proof. The guest media log's non-black pixel range, Android decoder format, renderer
callbacks, and an earlier diagnostic ADB capture of the actual Godot café teacher scene are the
relevant evidence; the screenshot compositing behavior remains unexplained.

## Shutdown

The final release timer was allowed to expire and then checked with:

```powershell
./scripts/m8-vm.ps1 -Action WaitRelease -Version 0.1.4 -SmokeSeconds 300
./scripts/m8-vm.ps1 -Action ReleaseStatus
./scripts/m8-vm.ps1 -Action Stop
```

The persisted evidence reported `task_state=Ready`, `listener_count=0`,
`owned_process_count=0`, and `clean_shutdown=true` at `2026-10-19T13:10:52.2794357Z`. The host
emulator was killed and the guest shut down normally. No media server or application tone remained.

## Harness defects found and corrected

- Clean llama startup exposed the missing VC++ prerequisite and too-short health window.
- Long SSH scripts exceeded a Windows encoded-command boundary; the harness now sends source over
  stdin and creates the remote script block there.
- The original ICE answer advertised guest `10.0.2.15`, unreachable from the host AVD; the
  loopback-only fixture candidate/UDP forward fixed the actual peer connection.
- A 60-second tone ran before slow guest ICE completed, while a 180-second attempt did not produce
  evidence before that run ended. The measured 90-second delay connected first and captured PCM.
- Noninteractive SSH launch of a second renderer failed ANGLE display creation and was not counted.
- A scheduled second-renderer attempt emitted its two-second PCM before the reader attached and was
  not counted.

No failed or diagnostic attempt is presented as physical, acoustic, GPU, or clean-run evidence.

## Final repository gates

```powershell
./scripts/test.ps1 -Scope all
uv run --frozen --extra media --extra speech pip-audit `
  --cache-dir .cache/pip-audit-m8-final
uv run --frozen pre-commit run --all-files
```

The first full attempt stopped on one Ruff line-length error. The second passed lint but stopped on
two format-check differences. After the pinned formatter changed only those files, the full suite
passed from the beginning: 169 Python tests at 85.51% branch coverage, 26 contract tests, 13 Kotlin
tests, 8 pure C# tests, 18 media tests, Godot import/build/self-test, and the Android debug APK
build. The audit reported no known vulnerabilities. Every pre-commit hook passed, including secret
and large-file checks, Ruff, formatting, and contract tests. `git diff --check` reported no
whitespace error; it printed only the checkout's expected LF-to-CRLF warnings.
