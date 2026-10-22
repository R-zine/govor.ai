# Milestone 9 physical release acceptance

- Physical execution date: 2026-10-21
- Post-audit packaging follow-up: 2026-10-22
- Learner phone picture/speech confirmation: 2026-10-22
- Milestone result: **complete**
- Raw reports (ignored): `.cache/m9-final-candidate-smoke.json` and
  `.cache/m9-physical-soak.json`

## Scope and configuration

This records Milestone 9 work on the target Windows PC and a physical Android phone. It establishes
only the rows directly measured below and does not convert earlier emulator or VM evidence into
physical evidence. The 1,800-second transport run is retained as historical evidence and is not
reported as a continuously interactive lesson.

| Component | Recorded configuration |
| --- | --- |
| Windows host | Process build 10.0.26200 |
| GPU | NVIDIA GeForce RTX 3060, 12,288 MiB, driver 560.94 |
| Phone | realme RMX3939, Android 16/API 36, 720x1600, density 320, security patch 2026-08-01 |
| Wi-Fi | `A1_B436`, WPA2-Personal, 2.4 GHz channel 7, 802.11ax |
| Addresses | PC `192.168.100.61/24`; phone `192.168.100.71/24` |
| Windows profile | Private |
| Android transport | Physical Wi-Fi; no `adb reverse` mapping |
| Measured release | Windows portable directory plus signed Android `0.1.10`/code 11 |
| Measured APK | 55,425,173 bytes; SHA-256 `2bbfb230925767f50613c0947702241103556ccb93c1840d97f495b524c2d50d` |
| Android decoder | Hardware `c2.unisoc.vp8.decoder` |
| Windows encoder | aiortc VP8 software encoding; hardware encoding false |

The ADB serial, pairing code, device credential, private key, raw microphone audio, and learner
transcript are deliberately absent from this record.

## Implementation completed for this run

- Android now owns its media ViewModel at Activity scope and retains the last connection request
  across normal lifecycle transitions. A pure `LifecycleReconnectPolicy` suppresses automatic
  reconnect after explicit disconnect, reconnects once on foreground, and retries when the default
  network becomes available. Release retries clear the one-time pairing code and reuse only the
  encrypted Android-Keystore device credential.
- Godot and Python now use renderer-video mapping version 2 with two alternating 1280x720 RGBA
  slots. Godot fills the inactive slot then commits the header; Python requires a stable header
  around the copied slot. The aiortc video track waits asynchronously for at most 20 ms for a new
  publication when sampling just before Godot, preventing deterministic 30 fps phase aliasing.
- Godot schedules fixed publication intervals with bounded catch-up. A direct mapping probe
  measured 30.017 publications per second, 33.119 ms median interval, and 38.789 ms maximum in its
  sample.
- The loopback-only media metrics endpoint reports active connection/microphone state, emitted and
  unique renderer frames, interval percentiles, audio source/silence counts, RTP loss/RTT,
  DTLS state, codec, and the Windows hardware-encoding flag. It does not add a LAN route.
- `scripts/hardware-test.ps1` rejects emulators, reverse mappings, non-Wi-Fi devices, absent signed
  app/listener/session state, and delegates with hashtable splatting. `scripts/benchmark.ps1`
  accepts bounded duration/sample/output parameters and records Windows, NVIDIA, Android,
  network, codec, RTP, renderer, and microphone measurements.

Changed implementation paths are:

- `apps/android/app/src/main/kotlin/ai/govor/app/MainActivity.kt`
- `apps/android/app/src/main/kotlin/ai/govor/app/MediaSessionViewModel.kt`
- `apps/android/core/src/main/kotlin/ai/govor/core/LifecycleReconnectPolicy.kt`
- `apps/android/core/src/test/kotlin/ai/govor/core/LifecycleReconnectPolicyTest.kt`
- `apps/renderer/Scripts/RendererBridgeProtocol.cs`
- `apps/renderer/Scripts/RendererSelfTest.cs`
- `apps/renderer/Scripts/SharedMemoryVideoPublisher.cs`
- `services/media/src/govor_media/app.py`
- `services/media/src/govor_media/peer.py`
- `services/media/src/govor_media/renderer_bridge.py`
- `services/media/tests/test_peer.py`
- `services/media/tests/test_renderer_bridge.py`
- `services/media/tests/test_signaling.py`
- `scripts/hardware-test.ps1`
- `scripts/benchmark.ps1`

## Commands and artifacts

Representative exact commands:

```powershell
./scripts/package.ps1 -Version 0.1.10 -VersionCode 11 -NoArchive `
    -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
./scripts/hardware-test.ps1 -DurationSeconds 30 -SampleIntervalSeconds 5 `
    -OutputPath .cache/m9-final-candidate-smoke.json
./scripts/hardware-test.ps1 -DurationSeconds 1800 -SampleIntervalSeconds 5 `
    -OutputPath .cache/m9-physical-soak.json
./scripts/test.ps1 -Scope all
$env:UV_CACHE_DIR = Join-Path (Resolve-Path '.cache').Path 'uv-m9-final'
uv run --frozen --extra media --extra speech pip-audit `
    --cache-dir .cache/pip-audit-m9-final
$env:PRE_COMMIT_HOME = Join-Path (Resolve-Path '.cache').Path 'pre-commit-m9-final'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'safe.directory'
$env:GIT_CONFIG_VALUE_0 = 'C:/Users/PC/Documents/GitHub/govor.ai'
uv run --frozen pre-commit run --all-files
```

The 30-second candidate smoke passed with 948 emitted video frames (31.204 fps), 913 unique Godot
frames (30.052 fps), 1,507 new physical microphone frames, zero reported RTP loss, video/audio RTT
15.321/14.165 ms, and five successful Wi-Fi samples. It existed to reject short-startup/cadence
regressions before the soak; lifetime maximum interval included a pre-benchmark connection
transition and is not used as its steady-state cadence result.

## 30-minute transport/media soak

- Start: `2026-10-21T17:11:24.8020983Z`
- Finish: `2026-10-21T17:41:24.9101548Z`
- Measured duration: 1,800.064658 seconds
- Samples: 292 at a requested five-second interval

| Metric | Actual result |
| --- | --- |
| Video frames emitted | 54,035; 30.018 fps |
| Unique renderer frames | 53,508; 29.726 fps |
| Renderer interval | p50 33.333 ms; p95 33.349 ms; max 133.335 ms |
| Physical microphone frames | +89,863 at 48 kHz |
| Video RTP | 145,989 received; 0 lost; final RTT 13.247 ms |
| Audio RTP | 97,775 received; 0 lost; final RTT 8.985 ms |
| Transport/security | DTLS connected; authenticated release WSS; VP8 |
| Wi-Fi ping | 292 success, 0 failure; p50 3 ms; p95 12 ms; max 44 ms |
| Windows working set | start 3,560,075,264; end 3,625,168,896; max 3,628,318,720 bytes |
| Windows CPU | p50 4.168%; p95 4.595% |
| Android total PSS | start 123,086; end 120,787; max 123,086 KiB |
| NVIDIA VRAM | start 5,116; end 4,632; max 5,296 MiB |
| NVIDIA utilization | p50 20%; p95 44%; maximum observed temperature 62 °C |
| Phone temperature/battery | maximum 27.9 °C; battery observations 48–52% |
| Codec selection | Android hardware VP8 decode; Windows VP8 software encode fallback |

Renderer frames, physical microphone frames, and DTLS transport advanced while the application was
not the Windows foreground window. The monitor was turned off during the run; the same counters
continued advancing. A broadcast `SendMessage` helper blocked on an unrelated unresponsive
window, so it was stopped and display recovery used bounded `SendMessageTimeout`. This tooling
failure did not interrupt the media session.

This was a passing 30-minute transport/media run. It was **not** a continuously interactive
lesson: the phone waited for learner responses and one Retry action was used. On 2026-10-22 the
product owner removed fixed-duration lesson/soak acceptance. This run remains additional
historical stability evidence rather than a current release gate.

## Physical interaction, recovery, and audio independence

- A supervised physical session replayed a word and submitted three hold-to-talk recordings. The
  host received the real phone microphone and advanced café progress to 2/3. No recording or full
  transcript was retained in this report.
- Android Settings backgrounded the same Activity. Media became inactive as designed; returning
  with Back reconnected the same process, restored DTLS/microphone flow, and retained café 2/3.
- Disabling phone Wi-Fi removed its WLAN IPv4 address. ICE transition was delayed, then recovery
  on Wi-Fi restoration established a new authenticated peer without pairing again and retained
  café 2/3.
- Explicit Disconnect suppressed lifecycle reconnect. Tapping Connect reused the stored encrypted
  credential and restored renderer/microphone/DTLS counters.
- The manifest-locked portrait UI remained portrait under physical rotation attempts.
- The Windows default playback endpoint was muted from its exact prior state, the phone lesson
  advanced through teacher playback to learner input, and the prior mute state was restored. The
  application captures only the phone WebRTC microphone and opens no PC microphone. This is direct
  evidence that phone delivery does not require PC playback, plus architectural evidence for PC
  microphone independence; a separate physical disable-PC-microphone action was not performed.

Automation cannot establish subjective perception. On 2026-10-22 the learner confirmed that the
moving teacher/environment was visible on the physical phone and that teacher speech was audible,
clear, and intelligible there.

## Failures and corrections

- Early cadence runs exposed producer/consumer phase aliasing and full-frame copy contention. The
  two-slot protocol and bounded publication wait corrected the issue; deterministic tests cover
  inactive-slot writes, stable-header validation, and a publication arriving 5 ms after a media
  tick.
- The first hardware wrapper implementation used array splatting and sent `-Profile` as a literal
  positional value. Hashtable splatting fixed it before recorded acceptance data.
- An explicit `am start ai.govor.app/.MainActivity` created a second Activity during one lifecycle
  attempt. Back returned to the original connected Activity; only that correct same-Activity path
  is acceptance evidence.
- The first final dependency audit failed with `PYSEC-2026-4320` for certifi 2026.7.22 and
  `GHSA-vxj4-q4g9-crj7` for virtualenv 21.14.6. Certifi is pinned at 2026.10.19 and virtualenv is
  locked at 21.14.12; the repeat audit reported no known vulnerabilities.
- The first post-audit `0.1.11` launcher attempt hit an isolated Windows asyncio
  `Accept failed on a socket`/WinError 64 and failed its media health deadline. A retry started the
  media/host/model/renderer stack successfully and its localhost TLS health probe passed with the
  packaged Python runtime. This transient remains recorded; it is not hidden as a passing attempt.
- A diagnostic `--smoke-seconds 600` invocation was correctly rejected because release smoke
  duration is capped at 300 seconds. That was operator/harness misuse, not a product acceptance
  result.

## Post-audit candidate and verification

The post-audit package command was:

```powershell
./scripts/package.ps1 -Version 0.1.11 -VersionCode 12 -NoArchive `
    -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
```

Godot export, signed Android release build/lint/signature verification, pinned dependency/source
staging, release imports, prerequisite checks, and both learner wrapper doctor smokes passed. The
APK is 55,425,173 bytes with SHA-256
`94662d516bfff260b3276522142bb7ce34a995f03400011df914940c10b87e2a`, version 0.1.11/code 12,
and the same RSA-3072 signer as the measured candidate. It was installed successfully on the
physical phone. The first attempt stopped at the phone PIN screen; after the user unlocked the
phone on 2026-10-22, the exact candidate completed the follow-up below. No PIN was requested,
guessed, or logged.

## Exact 0.1.11 physical follow-up

The signed post-audit candidate connected through `192.168.100.61:8765/8766` on the intended
Wi-Fi, with no `adb reverse` mapping and no new pairing code. It reused only its stored encrypted
device credential. The exact benchmark command was:

```powershell
./scripts/hardware-test.ps1 -DurationSeconds 30 -SampleIntervalSeconds 5 `
    -OutputPath .cache/m9-011-physical-smoke.json
```

- Start: `2026-10-22T11:22:36.2026713Z`
- Finish: `2026-10-22T11:23:06.8499979Z`
- Measured duration: 30.6085149 seconds
- Five successful samples; Wi-Fi ping p50/p95/max 6/32/32 ms
- 933 emitted frames (30.482 fps) and 917 unique Godot frames (29.959 fps)
- +1,532 physical 48 kHz microphone frames
- Zero reported video/audio RTP loss; final RTT 8.214/19.202 ms
- DTLS connected, VP8, Android hardware decode, explicit Windows software-encode fallback
- Windows RAM max 3,535,134,720 bytes and CPU p95 4.649%
- Android PSS max 113,082 KiB, VRAM max 5,206 MiB, GPU p95 57%, phone max 27.7 °C

The same exact candidate then completed the café lesson using bounded acoustic utterances
captured by the physical phone microphone. A deliberately wrong phrase did not advance the
exercise. The flow entered Bulgarian clarification after recognition ambiguity, returned to
English, completed 3/3, and showed `Lesson complete · progress saved`. The release progress
database then reported `cafe-ordering` with `completed_count=1`, `exercise_index=3`, and three
successful exercises; it contains structured outcomes/vocabulary, not raw audio or full
transcripts.

After a clean package stop/start, the phone reconnected without a new pairing code. The completed
café marker and database completion persisted; **Retry lesson** began a new 1/3 attempt. Tapping
`Welcome` displayed `Welcome /wˈɛlkʌm/` and Bulgarian pronunciation guidance. A second bounded tap
at 0.75× produced a phone `AudioTrack` using speech/media audio at 24 kHz and the player stopped and
released afterward. This is direct isolated-word playback evidence, not a subjective clarity
claim.

The product owner removed the fixed 30-minute continuous-lesson requirement on 2026-10-22.
Milestone 9 now requires recorded bounded interaction, stability, lifecycle, resource, and clean
teardown evidence. The earlier 1,800-second transport record exceeds the current bounded-stability
requirement but is not relabeled as an interactive lesson.

The final acceptance text specifically requires the learner to ask a clarification question in
Bulgarian. In a later unlocked-phone run, a bounded local Piper utterance saying
`Какво означава order?` traversed hold-to-talk and the physical phone microphone. A repeated first
attempt was mis-transcribed as Korean text. The clean single attempt appeared as
`(speaking in foreign language)` rather than preserving the words, but the exact candidate
supplied Bulgarian guidance and returned to the English prompt `Say: I would like a coffee,
please.` This closes the explicit Bulgarian-help/English-return interaction with a recorded
recognition limitation; it is not a human-speech accuracy claim.

A bounded local Kokoro response was then recognized as `Would you like a coffee, please?`, the
teacher reacted appropriately, and the same attempt advanced to café 2/3. Tapping `Would`
displayed `Would /wˈʊd/` with Bulgarian pronunciation guidance. A second bounded Kokoro response
was recognized as `That's all, thank you`, advancing to 3/3 and demonstrating continued lesson
progress. The earlier exact-candidate run already supplied direct 24 kHz isolated-word playback,
completion persistence, restart, and clean reconnect evidence. Together the exact-candidate runs
cover the ordered final scenario without claiming that Whisper accurately transcribed the Piper
sentence.

During the follow-up, transient recoverable lesson states passed **Retry lesson**. One Windows
SAPI background job failed to initialize and supplied no speech; it is a failed attempt, not
evidence. Afterward the Android app and release package stopped, ports 8765-8768 and owned process
checks were empty, stay-awake/rotation were restored, and all temporary utterance files were
deleted.

The source full suite passed both before and after the advisory-only lock remediation. The final
post-remediation run reported 169 Python tests at 85.51% branch coverage, 26 contract tests, 17
Kotlin tests, 8 C# tests, 21 media tests, Godot import/build/self-test, and the Android debug build.
The post-remediation dependency audit reported no known vulnerabilities. Final post-documentation
pre-commit passed JSON/YAML, end-of-file, line-ending, whitespace, private-key, large-file, Ruff,
format, and 26 contract-test hooks. The all-files run was repeated after recording the final
bilingual physical follow-up and passed the same hooks.

## Acceptance state and cleanup

Milestone 9 is complete. The learner confirmed moving phone video and clear, intelligible phone
speech on 2026-10-22. The exact candidate has the explicit Bulgarian-help/English-return flow with
its Whisper transcript limitation recorded. The final suite/audit/pre-commit gates pass, and all
physical rows, including café completion/restart and bounded stability, have direct evidence.

Cleanup after the recorded work found zero release listeners, zero Godot/llama/package-owned
processes, and a force-stopped Android app. Stay-awake and rotation settings were restored. No
tone, media service, or PC audio remained active.
