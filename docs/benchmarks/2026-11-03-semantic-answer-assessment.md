# Semantic answer assessment — 2026-11-03

The café report reproduced a discarded model verdict: the service called Qwen but then used only
literal patterns requiring coffee. The correction passes its strict JSON boolean through the
existing help/language guards into the teaching engine. See ADR-0022.

## Fixture and machine

- Development Windows PC, Windows NT 10.0.26200.0 x64, NVIDIA RTX 3060 (12 GiB).
- Pinned llama.cpp b11540 Vulkan, Qwen3 4B Q4_K_M, loopback `127.0.0.1:8767`.
- Model SHA-256: `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.
- Server flags: `-ngl 99 -c 4096 --jinja --no-webui --log-disable`.
- Production dialogue adapter, closed schema, greedy temperature 0, top-p 0.8, top-k 20, seed 42.
- Synthetic text fixtures only. No phone, microphone, recognition, TTS, media server, or player
  was used. No cloud call or learner database write occurred.

## Results

| Check | Final result |
| --- | --- |
| Semantic fixtures, 2026-11-03 21:24:19 UTC | 28/28 passed |
| Valid paraphrases/choices | 18/18 accepted, including the reported tea order |
| Wrong/incomplete/help/injection cases | 10/10 retained the exercise |
| Every bundled exercise | All 12 exercised with the actual domain engine/context |
| Semantic adapter latency | Median 1,062.2 ms; maximum 3,349.2 ms (includes first inference) |
| Existing bilingual fixtures, 21:24:27 UTC | 7/7 intent/locale/advance checks passed |
| Bilingual adapter latency | Median 921.4 ms; maximum 1,423.2 ms |
| Focused domain/service/provider/schema tests | 100 passed |
| Ruff, format, strict mypy | Passed; 57 typed source files |
| Frozen media/speech dependency audit | No known vulnerabilities |
| Full software suite | Passed: 341 Python at 85.57% coverage, Kotlin/JVM, 11 C#, 21 real media, Godot import/build/self-test, Android debug build |

The focused commit runs the installed pre-commit quality/contract/affected-test hooks. Its output
is captured in `.cache/semantic-answer-commit.log`.

The semantic fixture set adds unseen paraphrases after the initial prompt revisions; it contains
yes/no and choice answers, a quantity without “kilo,” personal destinations, polite contractions,
home requests/routines, wrong-context answers, negation, missing information, help, and a grading
override. Its engine result, not just the model flag, determines whether the case passes. Unit
integration tests also verify progress survival and a newly imported JSON lesson's own question
and goal. Those tests use clearly named recognizer/dialogue fakes and are not real-provider proof.

## Commands and artifacts

The executed bounded wrapper was `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
.cache/run-answer-assessment.ps1`. It initialized `scripts/common.ps1`, started the server hidden,
waited for `/health`, ran these two commands, and stopped its owned PID in `finally`:

```powershell
uv run --frozen python scripts/local_ai_benchmark.py --dialogue-only `
  --whisper-executable (Get-GovorWhisperCli) --whisper-model (Get-GovorWhisperModel) `
  --fixtures tests/fixtures/ai/answer-assessment-cases.json `
  --output .cache/answer-assessment-cases-results.json
uv run --frozen python scripts/local_ai_benchmark.py --dialogue-only `
  --whisper-executable (Get-GovorWhisperCli) --whisper-model (Get-GovorWhisperModel) `
  --fixtures tests/fixtures/ai/bilingual-cases.json --output .cache/bilingual-cases-results.json
uv run --frozen pytest packages/domain/tests/test_teaching.py services/local_ai/tests/test_service.py services/local_ai/tests/test_llama_cpp.py tests/contracts -q
uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-answer-assessment
./scripts/test.ps1 -Scope all
```

For reproduction, initialize the repository environment and set `PYTHONPATH` to the same source
directories used by `scripts/benchmark.ps1 -Profile local-ai`; start `(Get-GovorLlamaServer)` with
`-m (Get-GovorLlamaModel) --host 127.0.0.1 --port 8767` plus the flags above. Wait for successful
`/health` before the fixture commands and always stop that owned server in `finally`. The Whisper
arguments are required by the existing benchmark CLI but unused with `--dialogue-only`.

Ignored raw reports are the two output paths above. Server logs are
`.cache/answer-assessment-llama.stdout.log` and `.cache/answer-assessment-llama.stderr.log`;
the full-suite log is `.cache/semantic-answer-full-tests.log`. They contain fixture IDs/outcomes,
not learner recordings or transcripts. Server teardown left no owned llama process or listener.

## Failed attempts and limits

The initial prompt accepted all 13 original valid answers but also accepted two incomplete
answers and a grading override. Five further reported failures were a harness error comparing
non-attempt `None` to false; the benchmark now compares actual success explicitly. Later prompt
revisions reached 20/21 but rejected a valid dine-in contraction. A compact version passed 28/28
while misclassifying the old vague-answer fixture as `english_answer` with false rather than
`ambiguous`; the final classification prompt and greedy sampling passed both complete sets.
An ignored diagnostic helper initially omitted the required `intent_hint` constructor argument;
it was corrected before its inspection run. The first dependency audit was denied network sockets
by the sandbox (WinError 10013); the approved network rerun passed.
The first all-scope attempt passed Python but the sandbox denied Kotlin's daemon timestamp under
the user profile. The rerun with normal build-cache access completed. Nonfatal Starlette
deprecation and pytest-cache access warnings were retained in that run's log.

This is a small development-machine sample, not a broad accuracy or pedagogical study. Model
judgment and recognition remain fallible; the literal fallback remains narrower than semantic
assessment. Nothing here establishes new physical-phone, acoustic, recognition, latency-acceptance,
or subjective speech-quality evidence. Source changes are not installed into release 0.1.22 by
these tests; deployment requires rebuilding the host. No Android code or wire shape changed.
