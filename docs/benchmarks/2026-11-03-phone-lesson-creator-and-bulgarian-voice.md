# Phone lesson creator and Bulgarian voice presentation — 2026-11-03

## Scope

This is development-machine software evidence for two post-milestone corrections:

- create a local-LLM lesson from the authenticated Android lesson-selection screen; and
- keep Bulgarian neural speech intelligible while linking its presentation to the selected
  female/male teacher.

It is not a physical-phone UI, acoustic, intelligibility, or release-package result. No service,
media listener, or audio player was started by these checks. Automated synthesis wrote ignored WAV
fixtures but did not play them.

## Implementation result

The version 1 control union now includes bounded `lesson.create.request` and
`lesson.create.result` variants. `lesson.catalog` advertises the current validated environment
choices. Android places a create action beside the lesson selector, accepts a required topic plus
optional difficulty/environment/one-to-eight exercise length, displays in-progress/success/failure
without entering the lesson error state, and selects the created scenario after the host broadcasts
the refreshed catalog.

The release host accepts creation only before a lesson on the already authenticated WSS connection,
allows one in-flight job per connection, calls the existing loopback-only llama.cpp creator, and
publishes through the same validated additive importer. It adds no HTTP endpoint, file/path field,
cloud call, or phone-side import/update authority.

Bulgarian speech continues to use the installed Piper Dimitar neural model. Elena and Amira apply
an in-process 3.5/2.5-semitone phase-vocoder presentation respectively; Daniel uses the unmodified
waveform. Frame count and model-derived timing remain unchanged. If Piper fails, every profile uses
normal eSpeak `bg`; the previously unintelligible `bg+f3` failure route is removed.

## Commands and results

```powershell
$env:UV_CACHE_DIR=(Resolve-Path '.cache').Path+'\uv-feature'
uv run --frozen ruff check apps/host/src apps/host/tests packages/contracts/python tests/contracts
uv run --frozen pytest tests/contracts apps/host/tests/test_app.py -q
```

Passed: Ruff and 80 focused Python/contract/host tests. The only warning was the existing Starlette
TestClient/httpx deprecation.

```powershell
./scripts/test.ps1 -Scope python
```

Passed: Ruff, format, strict mypy, and 315 tests at 85.07% branch coverage. The only warning was
the existing Starlette TestClient/httpx deprecation.

```powershell
./scripts/test.ps1 -Scope kotlin
```

Passed outside the managed sandbox: 29 Gradle tasks covering core and application JVM tests. The
first sandboxed run compiled Kotlin via the documented in-process fallback, then failed because the
sandbox denied Gradle access to a transformed lifecycle JAR. That failure is not reported as a
test pass; the unrestricted retry completed successfully.

```powershell
./scripts/test.ps1 -Scope all
```

Passed: 315 Python tests at 85.07% coverage, Kotlin/JVM tests, 10 C# tests, 21 media tests, Godot
import/build/headless self-test, and Android debug assembly. Warnings were the existing Starlette
deprecation, pytest cache permission warning, offline NuGet advisory-index warning, and expected
unstripped Android native libraries.

```powershell
./scripts/benchmark.ps1 -Profile speech
```

Passed against the real installed models. The Bulgarian 1.0 sample reported provider
`piper-bg_BG-dimitar-medium-female-presentation`, 22,050 Hz, 2,612,244 µs, 115,244 WAV bytes,
SHA-256 `7f060814a672e4a7a62c7916126369470c33fac0e2372c105ea82b4e57d2d99d`, 1,034.7 ms warm
latency, five word alignments, 30 phoneme alignments, and `fallback_used=false`. The 0.75 and 1.25
samples also passed. Exact machine-readable output is ignored at `.cache/speech-benchmark.json`;
the 1.0 sample is ignored at `.cache/speech-samples/piper-bg-bg.wav`.

The first live dependency audit found `GHSA-45c3-73f7-pv4m` in transitive dnspython 2.8.0. The
lockfile was upgraded to dnspython 2.9.1, then the 21 media tests passed again and the repeated audit
reported no known vulnerabilities. The all-files pre-commit gate subsequently passed every hook,
including affected-application tests. The initial sandboxed audit/pre-commit attempt could not
reach PyPI/GitHub and is not reported as a pass; approved-network retries produced the results
above.

## Research and limitations

The official Piper catalog still offers only Bulgarian Dimitar. BgTTS-38M-V2 has native Bulgarian
female examples and an Apache-2.0 model card, but its current inference path adds PyTorch,
MioCodec, WavLM and a pickle-format checkpoint. That dependency/model chain has not been pinned,
audited, packaged, benchmarked, or accepted by a learner, so it was not silently added to the
release. The phase-vocoder presentation adds no dependency or model download and retains Piper's
base articulation, but automated waveform checks cannot prove that it sounds female, natural, or
intelligible to the learner.

Remaining acceptance is therefore an interactive paired-phone run: create and open a lesson,
select Elena/Amira/Daniel, trigger Bulgarian guidance for each, and have the learner judge speaker
match and intelligibility. A future native female neural provider should replace the transform if
it passes those packaging and listening gates.
