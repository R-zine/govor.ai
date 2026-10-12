# ADR-0007: Local speech providers with conservative model timing

- Status: accepted for development; redistribution review required
- Date: 2026-10-12
- Milestone: 4

## Context

The teacher needs natural English and Bulgarian speech, deterministic offline recovery,
accent-aware IPA, synchronized word highlighting, speed control, and isolated-word replay. Timing
must come from the provider rather than character proportions or fabricated timestamps. The
Android client must keep playing when timing is unavailable, and locale identity must remain
explicit so British and American pronunciation do not silently mix.

The implementation must remain local and replaceable. Teacher audio crosses the existing bounded
control boundary as mono PCM16 WAV; the host must not depend on the Windows audio device. A
release decision must also account for the GPL licenses in the Bulgarian/fallback/phonemizer
stack rather than treating process isolation as a licensing workaround.

## Decision

Use pinned `kokoro-onnx==0.6.1` with the full Kokoro v1.0 ONNX model for English. `bf_emma` is the
`en-GB` voice and `af_heart` is the `en-US` voice. Use pinned `piper-tts[alignment]==1.8.0` with
`bg_BG-dimitar-medium` for Bulgarian. Model and voice files are checksum-pinned, downloaded to
ignored tooling storage, and never committed.

Use eSpeak NG 1.52 from `espeakng-loader==0.2.4` as the deterministic fallback. It runs in a
short-lived child process, receives bounded text over standard input, and returns WAV over standard
output. This keeps eSpeak's process-global C state out of the host and keeps teacher text out of
process arguments and logs. It does not change the GPL obligations if the component is distributed.

Use Phonemizer 3.4.0/eSpeak for per-word IPA with explicit `en-GB`, `en-US`, or `bg-BG` locale.
Pronunciation entries carry exact character ranges and optional Bulgarian-language articulation
notes. Unsupported or empty pronunciation output fails validation rather than creating a display
guess.

Accept only duration output reported by the active model. Kokoro's timed output and Piper's model
phoneme sample counts are converted to integer microseconds. Provider phonemes are grouped into
words only when provider boundaries produce exactly the same number of groups as independent text
tokenization. If that invariant fails, both word and phoneme alignment are `null`; playback and IPA
remain available. No timestamp interpolation is permitted.

Kokoro's floating-point end positions are bounded to the exact trimmed WAV duration during
microsecond conversion. This only removes a possible sub-sample rounding overshoot at the playback
boundary; it does not invent, redistribute, or interpolate timing.

Android writes the bounded WAV to a static `AudioTrack`. Its playback-head frame count is converted
to media microseconds for highlighting, so changing `PlaybackParams.speed` changes wall time but not
the alignment time base. The supported full-turn rates are 0.75×, 1×, and 1.25×. A full replay is
local and cannot advance the host state. Selecting a word sends only its validated turn/index and
rate; the host synthesizes that isolated word while leaving the lesson in `awaiting_learner`.

Version 1 `teacher.turn` now contains sample rate, pronunciations, nullable word/phoneme alignment,
and a fallback flag. `teacher.word_replay_requested` and `teacher.word_audio` are closed bounded
messages. WAV payloads are limited to 1,500,044 decoded bytes and 30 seconds.

## Rejected

- Estimating word or phoneme spans from text length: this would fabricate timing and drift visibly.
- Treating valid-looking IPA as sufficient quality evidence: curated accent regressions and actual
  generated audio are required as well.
- Using ordinary STT output as pronunciation scoring: transcription is not authoritative phonetic
  assessment.
- Running eSpeak's process-global library in the long-lived host: a subprocess gives deterministic
  teardown and avoids interfering with Phonemizer's own library instance.
- Silently mapping `en` to one English voice: explicit `en-GB` and `en-US` are retained end to end.
- Calling process isolation a GPL exception: Milestone 8 must comply with the GPL stack or select a
  distribution-compatible replacement.

## Evidence and limits

`./scripts/benchmark.ps1 -Profile speech` generated English GB/US, Bulgarian, and fallback WAVs.
Both neural engines returned real word and phoneme alignment for the benchmark phrases; all three
speed settings changed duration in the expected order. The eSpeak repeat was byte-identical and
reported timing as null. Curated `water thought schedule` IPA differed consistently between
British and American English, and the Bulgarian fixture returned non-empty per-word IPA.

`./scripts/emulator-speech-smoke.ps1` then delivered Kokoro speech to the API 34 native emulator.
Android logged seven provider-timed word highlights, normal completion, a 0.75× replay without a
second host completion event, word selection, and isolated-word completion. The script stopped the
app, servers, reverse mappings, and audio afterward.

Generated samples were played once synchronously on the development PC and every player closed.
That proves the listening path was exercised; an AI agent did not infer subjective quality. The
user listened and confirmed on 2026-10-12 that the GB-English and Bulgarian samples sounded good,
so the required intelligibility/acceptable-naturalness criterion is accepted.

The emulator is development evidence only. Physical speaker/microphone acoustics, Wi-Fi, target
latency/resources, codec behavior, lifecycle, and soak remain mandatory Milestone 9 work.
