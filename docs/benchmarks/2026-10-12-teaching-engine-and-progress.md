# Milestone 5 teaching and progress evidence — 2026-10-12

This is functional/software evidence, not a hardware or pedagogical-effectiveness benchmark.

## Environment

- Windows process build 10.0.26200.
- Repository: `C:\Users\PC\Documents\GitHub\govor.ai`.
- Python 3.12 locked environment managed by uv.
- Android Studio API 34 emulator `emulator-5554`, used only for a bounded UI visibility check.
- Physical phone, Wi-Fi, acoustics, codecs, thermals, and soak: not executed; Milestone 9 only.

## Implemented scope

- Four committed guided scenarios: café, supermarket, airport, and home.
- Three goal-directed exercises per scenario with objectives, vocabulary, examples, difficulty
  prompts, expected intent labels, accepted phrase patterns, misunderstandings, corrections,
  Bulgarian help, and completion conditions.
- Deterministic English-success, help, correction, completion, and explainable difficulty rules.
- SQLite settings, resume, exercise/comprehension counts, vocabulary history/review dates,
  completion history, and difficulty reasons. The schema has no transcript/audio field.
- Android scenario, `en-GB`/`en-US`, spaced-review controls, and host-owned progress display.
- Local view, JSON export, and confirmation-gated history deletion.

## Commands and results

| Command/check | Result |
| --- | --- |
| `./scripts/test.ps1 -Scope python` | Passed: Ruff, format, strict mypy, 111 tests, 85.69% branch coverage |
| `./scripts/test.ps1 -Scope contracts` | Passed: 18 schema/fixture tests, including valid and invalid lesson progress |
| `./scripts/test.ps1 -Scope kotlin` | Passed: 13 JVM tests (11 contract/state plus 2 speech timeline) |
| `./scripts/test.ps1 -Scope csharp` | Passed: 7 contract tests |
| `./scripts/build.ps1 -Target android` | Passed; updated debug APK compiled |
| `./scripts/test.ps1 -Scope all` | Passed: Python/contracts/Kotlin/C#/15 media tests/Godot self-test/APK build |
| `uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-m5-final` | Passed with approved network access: no known vulnerabilities |
| API 34 emulator install/start/UI hierarchy/force-stop | Passed: Café, Supermarket, Airport, Home, GB/US, and spaced-review controls visible; no media/audio server started |
| Listener cleanup check | Passed: ports 8765–8768 were not listening after the UI check |

Final debug APK:

- Path: `apps/android/app/build/outputs/apk/debug/app-debug.apk`
- Size: 58,726,666 bytes.
- SHA-256: `ee37f03b47176d30d20d902807d86f43d2bb1c039b2de5e2d1b7b8aa97ada3d8`.

Ignored development artifacts:

- `.cache/govor-m5-ui-final.xml`
- `.cache/pip-audit-m5-final/`

## Functional acceptance evidence

- Parameterized pure-domain tests finish all four scenarios with valid English productions.
- Bulgarian help and mixed/Bulgarian answers do not increment attempts or success and retain the
  current exercise.
- Two failures reduce difficulty and expose `repeated_difficulty`; two consecutive first-try
  successes increase it and expose `consistent_first_try_success`.
- The local lesson service completes café through recognition/dialogue/speech-shaped interfaces,
  records structured completion, and starts a fresh attempt after restart.
- A separate restart test closes/reopens SQLite during an interrupted lesson and resumes at the
  next exercise with `Welcome back`.
- A sentinel full transcript passed into the teaching engine is absent from the exported database
  history. CLI tests cover view/export and confirmation-gated deletion while preserving settings.
- Host integration verifies that completed progress is delivered in `teacher.turn`, then waits for
  final playback completion before sending `session.ended` with reason `completed`.

## Transient failures and corrections

- Direct Gradle/.NET commands initially lacked the repository's managed JAVA_HOME/DOTNET settings;
  the documented scripts supplied them and passed.
- Managed Windows denied the global Kotlin daemon marker directory. Gradle used its documented
  in-process fallback and completed successfully; this is an environment warning, not a test skip.
- The first Android scenario row placed Home outside the initial UI hierarchy. The controls were
  changed to two visible rows, the APK rebuilt, and all four choices appeared in the final dump.
- The first dependency audit was denied by sandbox networking. The same command passed with
  approved network access.

## Limits

The guided phrase matcher proves deterministic progression for committed exercises; it is not a
general fluency, grammar, or pronunciation score. No live human lesson, broad learning-outcome
study, physical phone, intended Wi-Fi path, hardware codec, acoustic check, target-load metric, or
soak ran here. Those limitations do not block Milestone 5 but must not be reported as satisfied;
the physical/target bundle later passed separately in Milestone 9.
