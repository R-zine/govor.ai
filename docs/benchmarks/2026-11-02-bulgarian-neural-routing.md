# Bulgarian neural routing correction

- Date: 2026-11-02
- Machine: Windows 11 build 26200, Intel64 Family 6 Model 151, Python 3.12.12
- Scope: local speech routing and installed-model synthesis only
- Not evidence for: subjective intelligibility, phone acoustics, network/media transport, or a
  signed release

## Change

Elena and Amira previously used eSpeak NG `bg+f3` for normal Bulgarian synthesis to keep the voice
presentation female. The product owner reported that speech as barely understandable. All three
teacher profiles now prefer the installed neural Piper `bg_BG-dimitar-medium` model; profile-aware
eSpeak remains only the provider-failure fallback. The temporary female-model/male-voice mismatch
is explicit until a reviewed female Bulgarian neural provider is integrated.

## Verification

| Command | Result |
| --- | --- |
| `./scripts/test.ps1 -Scope speech` | Passed: mypy and 14 speech tests. |
| `./scripts/benchmark.ps1 -Profile speech` | Passed; ignored report at `.cache/speech-benchmark.json`. |
| Listener/process cleanup query | No listeners on 8765/8766/8767 and no Godot/renderer/ffplay process. |

The real Piper measurements were:

| Speed | Latency | Duration | WAV bytes | Alignment | Fallback |
| ---: | ---: | ---: | ---: | --- | --- |
| 0.75 | 8,783.8 ms cold | 3,204,353 us | 141,356 | 5 words / 30 phonemes | false |
| 1.00 | 961.6 ms warm | 2,658,684 us | 117,292 | 5 words / 30 phonemes | false |
| 1.25 | 922.2 ms warm | 2,171,065 us | 95,788 | 5 words / 30 phonemes | false |

All three samples were non-empty mono PCM16 WAV at 22,050 Hz and reported provider
`piper-bg_BG-dimitar-medium`. The benchmark deliberately does not play audio and records
`manual_listening: not_executed_by_automated_benchmark`; the learner must confirm the improvement
in an end-to-end run. The measured samples reached full-scale PCM, so this run does not make an
unmeasured loudness or clipping-quality claim.
