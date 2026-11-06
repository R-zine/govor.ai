# Hosted CI workflow repair — 2026-11-06

Software verification on the Windows development checkout with Python 3.12.12. No physical
device, GPU, model inference, VM, audio playback, or performance acceptance is claimed.

## Failed run and diagnosis

The public Actions API for [run 42224355712](https://github.com/R-zine/govor.ai/actions/runs/42224355712)
reports source `76dd3e9bb93a4350b53c770145c3bf07c91c7c59`, created at 2026-11-06 13:17:50 UTC.
Android failed its Gradle launch with exit 126; Python and media failed their mypy steps. C#,
renderer, and pre-commit jobs passed. These are observed job/step annotations. The full-log API
returned HTTP 403, and no noninteractive GitHub credential was available; detailed hosted compiler
output was not obtained. The errors below were reproduced locally using the workflow's commands.

Each reproduction used a separate ignored environment selected with UV_PROJECT_ENVIRONMENT:
`.cache/ci-repair/python-minimal` or `.cache/ci-repair/media-minimal`. The original mypy commands
used `--no-incremental` with distinct cache directories, independent of the populated .venv.

| Original command/check | Observed result |
| --- | --- |
| `uv run --frozen mypy --no-incremental --cache-dir .cache/ci-repair/mypy-python` | Exit 1: 16 errors across five speech files; missing NumPy, eSpeak loader, phonemizer, Kokoro, and Piper imports, plus unmatched ignore categories |
| `uv run --frozen --extra media mypy services/media/src packages/contracts/python --no-incremental --cache-dir .cache/ci-repair/mypy-media` | Exit 1: govor_gateway_security cannot be found; checked 11 source files |
| `git ls-files --stage apps/android/gradlew` | Mode 100644; Ubuntu cannot directly execute this tracked wrapper |

## Repair and verification

Python and media CI now invoke `scripts/test.ps1` rather than maintaining separate, stale command
lists. Python sync/audit explicitly select the speech extra. PYTEST_ADDOPTS preserves the XML
coverage report alongside the normal coverage gate. The media scope includes gateway-security
sources. No application dependencies, lockfile, type-check rules, tests, or coverage floor changed.
The Gradle wrapper has Git execute mode 100755 and an explicit LF rule in .gitattributes, with its
blob unchanged (`f5feea6d6b116baaca5a2642d4d9fa1f47d574a7`).

| Repaired command/check | Result |
| --- | --- |
| `uv sync --dev --extra speech --frozen`, then `./scripts/test.ps1 -Scope python` | Exit 0 in the isolated Python environment: Ruff/format, 57-source strict mypy, 398 tests, 85.60% branch coverage; coverage.xml generated with PYTEST_ADDOPTS=--cov-report=xml |
| `./scripts/test.ps1 -Scope media` | Exit 0 in the isolated media environment: 13-source mypy and 21 real aiortc tests |
| `uv run --frozen --extra speech pip-audit --cache-dir .cache/ci-repair/pip-audit` | Exit 0: no known vulnerabilities |
| Git-for-Windows `bash -n apps/android/gradlew` | Exit 0; shell syntax only, not an Ubuntu build |
| `git ls-files --stage` and `git check-attr text eol -- apps/android/gradlew` | Mode 100755; text set, LF required |
| Workflow YAML parsing, canonical-command/speech-sync assertions, and coverage artifact check | Passed |
| `uv run --frozen pre-commit validate-config` and `git diff --check` | Passed |

Fixed runs also used distinct fresh MYPY_CACHE_DIR values. An initial PowerShell 5.1 capture
attempt stopped when successful uv installation status on stderr became NativeCommandError;
running the workflow's explicit sync step before the test command resolved that harness issue.
It was not a test/type-check failure. Existing Starlette and pytest-cache warnings remain visible.

Ignored logs: `.cache/ci-repair/python-original-mypy.log`, `media-original-mypy.log`,
`python-fixed.log`, `media-fixed.log`, and `python-audit.log`. The focused commit runs the
installed complete software gate for the shared workflow change.

## Remaining boundary

No push or hosted rerun was performed. Push the local commits with an authenticated owner account,
then inspect the new CI run. Local Windows checks and Git file-mode verification do not establish
a successful Ubuntu-hosted run. Node/action deprecation warnings in the original run were
nonfatal and remain separate from this repair.
