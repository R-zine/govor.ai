# Hardware test ledger

Milestone 9 hardware acceptance requires a physical Android phone and suitable Windows
GPU/audio/network conditions. Emulator and synthetic loopback results may diagnose code but do
not satisfy device criteria. ADR-0004 makes this a final release gate rather than a prerequisite
for Milestones 2-8.

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

### Milestone 9 acceptance results (not executed)

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
| 30-minute stability | not executed | No suitable end-to-end path |

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

All physical-device rows above remain not executed for Milestone 9. The emulator also does not establish
Wi-Fi behavior, acoustic audio quality, physical microphone behavior, encoder/decoder hardware
selection, performance, thermals, or stability.

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
- Physical Android, Wi-Fi, codecs, latency/resources, unfocused/monitor-off behavior, and soak:
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
unfocused/monitor-off behavior, and soak were not executed; the short emulator interval is not a
physical performance result.

Exact commands, artifacts, failures, and limitations are in
`docs/benchmarks/2026-10-09-godot-renderer-migration.md`. Every physical-device acceptance row
remains not executed for Milestone 9; this does not reopen the completed Milestone 1 proof.

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
hardware-codec, thermals, or target-lifecycle evidence. Every Milestone 9 row remains not executed.
Exact commands, transient failures, artifacts, and limitations are recorded in
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
Wi-Fi, codecs, concurrent target load, latency, thermals, lifecycle, and soak remain not executed.

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
naturalness. All such target-hardware rows remain not executed in Milestone 9.
