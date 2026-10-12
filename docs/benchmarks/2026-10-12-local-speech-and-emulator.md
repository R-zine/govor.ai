# Milestone 4 local speech and emulator evidence — 2026-10-12

## Scope and environment

- Windows 11 process build 10.0.26200.
- Intel64 Family 6 Model 151 Stepping 2 development CPU; Python 3.12.12.
- Android Studio AVD `Pixel_3a_API_34_extension_level_7_x86_64`, API 34,
  `emulator-5554`, connected through debug-only `adb reverse`.
- This is local software/native-emulator evidence. It is not physical-phone, Wi-Fi, acoustic,
  hardware-codec, target-performance, thermal, lifecycle, or soak evidence.

## Pinned assets

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Kokoro v1.0 ONNX | 325,505,369 | `beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a` |
| Kokoro voices v1.0 | 28,214,398 | `bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d` |
| Piper `bg_BG-dimitar-medium` ONNX | 63,221,984 | `4972fe764468e8501416407ad81662de94cc6c9cdc680fcf807daef04e319f13` |
| Piper voice config | 5,123 | `ec9a9abdd17384d3db225e83085b2f68b790b112f058417c3a8a2ac58b79e7f0` |

The Python adapters are `kokoro-onnx==0.6.1`, `piper-tts[alignment]==1.8.0`,
Phonemizer 3.4.0, and `espeakng-loader==0.2.4` with eSpeak NG 1.52.0. The GPL and model
redistribution implications are explicit in ADR-0007 and `THIRD_PARTY_LICENSES.md`; these ignored
development assets are not a distribution decision.

## Commands and results

```powershell
./scripts/test.ps1 -Scope speech
./scripts/benchmark.ps1 -Profile speech
./scripts/bootstrap.ps1 -IncludeLocalAi -NoDownload
./scripts/emulator-speech-smoke.ps1
./scripts/test.ps1 -Scope all
./scripts/benchmark.ps1 -Profile local-ai
uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m4-final
$changed = @(git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' ls-files --modified --others --exclude-standard)
uv run --frozen --extra media --extra speech pre-commit run --files @changed
```

- Speech gate: **passed**, strict mypy and 11 adapter/IPA/fallback tests.
- Offline bootstrap verification: **passed**, including exact sizes and checksums above.
- Real speech benchmark: **passed**; result JSON and generated WAVs are ignored under
  `.cache/speech-benchmark.json` and `.cache/speech-samples/`.
- Native-emulator smoke: **passed**; ignored logs/UI documents are
  `.cache/speech-emulator-android.log`, `.cache/speech-emulator-lesson.xml`, and
  `.cache/speech-emulator-window.xml`.
- Full repository suite: **passed**; 93 Python tests at 85.23% coverage, 12 Kotlin tests, 7 C#
  tests, 15 media tests, Godot import/build/self-test, and the Android debug APK build.
- Integrated local-AI regression: **passed**; both dialogue candidates passed 7/7, both real STT
  fixtures passed, and a Bulgarian/English host session emitted Piper/Kokoro audio with no retained
  recordings or leaked sessions.
- Dependency audit including media and speech extras: **passed**, no known vulnerabilities found.
- Pre-commit over every modified and untracked source: **passed**; all pinned hooks and JSON
  contract tests completed cleanly.

## Integrated host regression

The final `2026-10-12T12:46:12Z` local-AI regression replaced the historical diagnostic turn marker in
the live host path. Its Bulgarian reply used `piper-bg_BG-dimitar-medium`; its following English
reply used `kokoro-onnx-v1.0`. Both free-form model replies returned null word alignment because
the provider boundary groups did not exactly match independent tokenization. This is the specified
conservative behavior: valid audio and pronunciation data continue without fabricated timestamps.
The controlled speech benchmark and native-emulator turn independently prove the non-null timing
and synchronized-highlight path.

The final debug APK is 58,712,920 bytes with SHA-256
`9c206f7ff849e860c2ffd057a4011bf2dab02aed1feb7b8fa3bec3c071a874fc`.

## Real synthesis measurements

This final development run was recorded at `2026-10-12T12:48:26Z`. Latency is wall time and
includes cold initialization where applicable; it is not a target-hardware performance result.

| Provider/case | Rate | Latency ms | Audio duration µs | WAV bytes | Word/phoneme spans |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kokoro `en-GB`, `bf_emma` | 0.75× | 2,186.9 | 2,711,333 | 130,188 | 7 / 29 |
| Kokoro `en-GB`, `bf_emma` | 1× | 403.7 | 2,006,000 | 96,332 | 7 / 29 |
| Kokoro `en-GB`, `bf_emma` | 1.25× | 1,320.6 | 1,750,000 | 84,044 | 7 / 29 |
| Kokoro `en-US`, `af_heart` | 1× | 3,270.7 | 1,841,333 | 88,428 | 6 / 20 |
| Piper `bg-BG-dimitar-medium` | 0.75× | 7,407.5 | 3,181,133 | 140,332 | 5 / 30 |
| Piper `bg-BG-dimitar-medium` | 1× | 784.9 | 2,589,024 | 114,220 | 5 / 30 |
| Piper `bg-BG-dimitar-medium` | 1.25× | 829.0 | 2,182,675 | 96,300 | 5 / 30 |
| eSpeak NG `en-GB` fallback | 1× | 276.5 | 1,297,278 | 57,254 | null / null |

Every WAV was mono PCM16, non-silent, within the control limit, and at its reported rate (Kokoro
24 kHz; Piper/eSpeak 22.05 kHz). Both neural engines produced actual model-derived timing for the
phrases. Duration decreased monotonically as requested speed increased. The fallback repeated with
byte-identical SHA-256
`1f5f5d49f6f737e178027e9cf563b31bc1a6f8490baae274d91a9377fb5ac05c`
and deliberately returned null timing.

## IPA regression

The curated words were phonemized separately per locale:

- `en-GB`: `water` /wˈɔːtə/, `thought` /θˈɔːt/, `schedule` /ʃˈɛdjuːl/
- `en-US`: `water` /wˈɔːɾɚ/, `thought` /θˈɔːt/, `schedule` /skˈɛdʒuːl/
- `bg-BG`: `Добър` /dˈobər/, `ден` /dˈen/

Tests also require Bulgarian-language articulation notes for selected difficult English phones.
These assertions combine provider output with actual generated audio; syntactic IPA alone is not
treated as quality proof.

## Native-emulator playback evidence

Android logged real provider ID `kokoro-onnx-v1.0`, `alignment=true`, seven distinct highlight
indices based on `AudioTrack.playbackHeadPosition`, and normal completion. It then logged
`playback_rate=0.75`, a complete local replay with `notify_host=false`, selection of word index 0,
and a separately synthesized 938,666 µs word WAV completing successfully on the final run. The host received no
second lesson-completion event for the replay, so replay did not advance the lesson.

The Android app exposes the full subtitle, explicit word buttons, an IPA/explanation card, replay,
and 0.75×/1×/1.25× controls. Null alignment is covered by the pure Kotlin timeline test and real
fallback test: audio remains playable while highlight selection returns null.

The emulator used generated WebRTC diagnostic media solely to keep the established connection
surface active. The teacher WAV came from Kokoro over the bounded control message and played via
native `AudioTrack`. Cleanup force-stopped the app and both servers and removed reverse mappings;
ports 8765/8766 and Android audio were inactive afterward.

## Listening and limitations

The four saved GB-English, US-English, Bulgarian, and fallback WAVs were played once sequentially
with synchronous `System.Media.SoundPlayer`; each player was disposed before the next and no audio
process remained. The unnecessary `System.Windows.Extensions` assembly load reported missing, but
`System.Media.SoundPlayer` was already available and all four `PlaySync` calls completed.

This records execution of the listening path; subjective quality was not inferred by an AI agent.
After listening, the user confirmed on 2026-10-12 that the GB-English and Bulgarian samples sounded
good. That closes the required intelligibility/acceptable-naturalness criterion for Milestone 4.

Initial implementation failures were retained as engineering findings: eSpeak's British voice
must be selected by identifier `en` rather than locale label `en-gb`; UI automation must avoid a
non-ASCII multiplication-sign match under Windows PowerShell 5.1; and the emulator harness now
launches the venv `uvicorn.exe` directly so cleanup does not leave `uv run` wrapper processes.
One repeated emulator run exercised eSpeak fallback for the isolated word because Kokoro's final
floating-point phoneme timestamp rounded one microsecond beyond the trimmed WAV. The adapter now
bounds those model-reported positions to the exact WAV duration; a regression test reproduces the
overshoot, and the following emulator rerun used Kokoro for the word and passed with clean teardown.
The first dependency-audit request was denied by sandbox networking and passed with approved PyPI
access. Initial pre-commit attempts also encountered the managed account's inaccessible global
cache and a sandbox-incomplete local hook manifest; the command-scoped safe-directory setting and
approved repository-local hook cache then ran all hooks successfully without changing global Git
configuration.
