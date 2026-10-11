# Milestone 3 local AI and bilingual benchmark — 2026-10-11

## Scope

This record covers local dialogue candidates, multilingual recognition, and the host/provider
integration boundary. It is desktop development evidence. It is not physical-phone, Wi-Fi,
acoustic, final-renderer coexistence, production TTS, or release-performance evidence.

## Environment

- Timestamp in artifact: `2026-10-11T19:23:52Z`.
- OS: Microsoft Windows NT 10.0.26200.0.
- CPU: Intel64 Family 6 Model 151 Stepping 2, 20 logical processors.
- RAM: 34,135,166,976 total bytes; 17,511,297,024 available during the selected-model run.
- GPU: NVIDIA GeForce RTX 3060, 12,288 MiB; driver 560.94.
- llama.cpp: b11540 Windows Vulkan, 99 GPU layers requested, 4,096-token context.
- whisper.cpp: b5454 Windows x64 CPU.
- Selected model: Qwen3 4B Q4_K_M, 2,497,280,256 bytes, SHA-256
  `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
- Comparison model: Qwen3 1.7B Q4_K_M, 1,107,408,544 bytes, SHA-256
  `228fb5627f7510b8b3516cdb6435e4b0d2a2bf330fe5b0ab19284a3570a8bb1f`.
- Whisper multilingual small model: SHA-256
  `1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b`.

## Commands

```powershell
./scripts/bootstrap.ps1 -IncludeMedia -IncludeRenderer -IncludeLocalAi
./scripts/test.ps1 -Scope python
./scripts/benchmark.ps1 -Profile local-ai
```

Bootstrap pinned and checksum-verified the runtimes, two model candidates, recognizer model, and
audio fixtures. The benchmark started each llama.cpp server on loopback, stopped it in a `finally`
path, ran the same deterministic generation settings/fixtures against each candidate, and then ran
recognition plus host orchestration against the selected default. No benchmark process remained
listening on ports 8765–8768 after completion.

The full local launcher was also started with a non-secret 42-character development token. Host,
renderer, media, and llama.cpp health passed; host health reported `provider_mode=local`, loopback
scope, connected renderer, and the Whisper/Qwen/diagnostic-tone capability records. Stopping the
foreground host triggered cleanup, and no process or listener remained on ports 8765–8768. Godot
again printed the managed-environment log-directory and root-certificate-store warnings while its
renderer control connection still succeeded.

## Dialogue candidate comparison

| Candidate | Fixture outcomes | Median | Maximum | Policy-modified cases | Working set |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 4B Q4_K_M | 7/7 | 1,002.8 ms | 2,883.6 ms | 1 | 2,706,542,592 bytes |
| Qwen3 1.7B Q4_K_M | 7/7 | 688.5 ms | 2,639.7 ms | 3 | 1,314,185,216 bytes |

The cases cover an English answer, Bulgarian clarification, mixed Bulgarian/English reformulation,
repeat, slower speech, vocabulary explanation, and ambiguous input. Every response parsed through
the closed schema and produced the expected intent/locale/progress outcome. The deterministic
policy corrected one 4B result and three 1.7B results; this is recorded behavior, not hidden as a
model success.

Qwen3 4B remains the default because its direct structured/pedagogical compliance was better in
this narrow set and it fit the development GPU. During its run, llama.cpp used 2,706,542,592 bytes
working set (3,207,282,688 peak). NVIDIA-reported memory rose from 1,766 to 4,798 MiB, a 3,032 MiB
delta. The smaller model is retained only as a reproducible comparison candidate. This selection
must be revisited if broader lesson-quality or Milestone 9 concurrent-render/encode evidence favors
1.7B.

These seven fixtures are not a general English/Bulgarian quality score. They do not by themselves
establish long-conversation coherence, every dialect, or pedagogical naturalness. The two-turn host
run below adds bounded-history integration evidence, while broader teaching evaluation remains for
later scenarios.

## Recognition

| Fixture | Source | Duration | Result | Latency |
| --- | --- | ---: | --- | ---: |
| `english-jfk` | whisper.cpp b5454 human recording (`jfk.wav`) | 11.000 s | English detected; required words present | 5,945.9 ms |
| `bulgarian-voxforge` | VoxForge `dtd-20120908-cuf`, headset microphone | 5.250 s | Bulgarian detected; required words present | 5,661.9 ms |

Median recognition latency was 5,803.9 ms. The English fixture produced its expected sentence. The
Bulgarian reference is “Аз с щипци отключвам много лесно всякакви врати.”; recognition was close
enough to contain the asserted stable words “отключвам” and “лесно” but had word errors. Therefore
this passes the bounded language/keyword check, not a claim of perfect transcription or a measured
word-error rate.

The fixture set does not yet include legally sourced hesitant speech, short speech,
Bulgarian-accented English, or a spoken mixed-language utterance. The curated text cases cover
mixed-language dialogue behavior; they are not audio recognition evidence for that category.

## Host integration and failure behavior

The host smoke used the real `Settings(mode="local")`, Whisper recognizer, Qwen3 4B provider,
deterministic policy, session memory, and orchestration. It processed the Bulgarian fixture and
then the English fixture in one session, returned a Bulgarian teacher locale and then English,
dispatched the expected renderer states, retained zero recordings, and left zero active sessions.
Transcript text was intentionally absent from the artifact.

Automated tests additionally cover:

- closed structured output and rejection of injected renderer/control fields;
- timeouts, server failures with one bounded retry, malformed JSON, and resource exhaustion;
- deterministic fallback, no-speech recognition without an invented transcript, and temporary
  WAV/JSON deletion;
- clarification/reformulation/help never advancing the exercise;
- bounded/clearable conversation memory and return to English;
- bounded loopback media capture and resampling of actual incoming audio frames.

Teacher audio in this milestone remains provider ID `milestone3-diagnostic-tone`: a bounded 150 ms
transport marker that is never represented as speech. TTS, naturalness, phonemes, replay, and speed
are explicitly not executed and begin in Milestone 4.

## Privacy and limitations

The benchmark made zero cloud requests after artifact download, retained zero recordings, and did
not write full transcripts. llama.cpp logging was disabled and all four redirected model log files
were zero bytes. llama.cpp and internal microphone capture were loopback-only. The
audio fixtures remain ignored local files and are not packaged.

No physical Android phone, Wi-Fi path, acoustic loop, hardware codec, final concurrent Godot/media
load, target latency, thermals, monitor-off behavior, or soak was run. Those remain mandatory
Milestone 9 release criteria and cannot be inferred from these desktop results.
