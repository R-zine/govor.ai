# Staged commit checks — 2026-11-06

This is software/tooling evidence on the existing Windows development checkout, using PowerShell
5.1, managed Python 3.12.12, the pinned Android/Gradle toolchain, .NET 8, and Godot 4.7.2 .NET.
It is not a device, audio, latency, inference, or performance benchmark.

## Changes and selection boundary

The existing affected-test dispatcher now uses component dependencies and staged paths, including
deletions and both sides of renames. It selects Python component/consumer directories instead of
the entire host suite, with whole-host mypy and Ruff checks. Isolated tests select their owning
suite. Shared contracts/dependencies/workflows/test infrastructure and unclassified runtime paths
retain the complete software gate. Dependency changes additionally select pip-audit. Python-only
checks do not initialize Java. The full suite retains its 85% coverage floor; partial selections
make no whole-tree coverage claim.

Android runs core/app JVM tests, lintDebug, and assembleDebug together; CI uses the same tasks.
The standalone contract hook was redundant and was removed. Hygiene gained TOML/XML parsing,
case-conflict and merge-marker checks. Ruff's hook version now matches pyproject.toml (0.13.3).
The hook remains Windows-local; CI's dedicated Linux hygiene job skips the two Windows hooks.

Selection is conservative at the component-suite level, not individual test functions. The
maintained table in `scripts/pre-commit-tests.ps1` must include new imports/resources; regressions
compare it with real Python imports, including lazy imports. No runtime dependency or wire
contract changed. No hardware/VM/model/acoustic test runs implicitly.

## Executed checks

Verification was reviewed at 2026-11-06 13:39 UTC; the focused commit subsequently invokes the
installed final staged checks. Development caches were initialized with scripts/common.ps1;
Git used command-scoped safe.directory and hook caches stayed under ignored .cache.

| Command | Result |
| --- | --- |
| `./scripts/check-powershell-syntax.ps1 scripts/pre-commit-tests.ps1 scripts/test.ps1` | Passed |
| `uv run --frozen ruff check tests/integration/test_pre_commit_dispatch.py` and `ruff format --check` | Passed |
| `uv run --frozen --extra speech pytest tests/integration/test_pre_commit_dispatch.py -q` | Final focused run: 51 passed; selection, imports, duplicates/overlap, deleted-only index, deleted integration test, cross-app rename, caller Git-environment isolation, Git failure, nonzero suite propagation, parser failure |
| `./scripts/pre-commit-tests.ps1 services/speech/tests/test_speech.py` | Passed: selected only services/speech/tests, 19 tests, Ruff/format/mypy; no Android/Godot/media suites |
| `./scripts/test.ps1 -Scope all` | Initial integration passed: 388 Python tests before the final import/ignore cases were added, 85.60% coverage; JVM/lint/build, 13 C#, 21 media, Godot passed |
| `uv run --frozen pre-commit validate-config` | Passed |
| `uv run --frozen pre-commit install --install-hooks` | Installed .git/hooks/pre-commit; pinned environments installed |
| `uv run --frozen pre-commit run --files README.md CONTRIBUTING.md docs/development/commands.md docs/development/setup.md docs/testing/strategy.md --verbose` | Exit 0; hygiene passed, software suites skipped; affected hook reported 0.27 seconds |
| `uv run --frozen pre-commit run --all-files --verbose` | Every software check/audit passed before the final deletion regression: 397 Python tests, 85.60% coverage, JVM/lint/debug build, 13 C#, 21 media, Godot self-test, no known vulnerabilities. Overall exit 1 because AGENTS.md was edited concurrently during this manual invocation; pre-commit correctly detected the tree modification. The final staged commit reruns checks without concurrent edits |
| `git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' diff --check` | Passed |

Ignored logs: `.cache/pre-commit-full-tests.log`, `.cache/pre-commit-selected-tests.log`, and
`.cache/pre-commit-all-checks.log`. Android lint HTML/XML reports are under
`apps/android/app/build/reports/`: zero errors and 28 warnings. No lint baseline or suppression
was introduced. Existing Starlette deprecation, inaccessible pytest cache, and NuGet advisory
service warnings were not hidden; NuGet's unavailable advisory endpoint is not a successful .NET
dependency-vulnerability audit.

## Resume

Install once in another clone with `uv run --frozen pre-commit install --install-hooks`. Preview
the current index with `./scripts/pre-commit-tests.ps1 -Staged -ListOnly`; `git commit` executes
the checks on the staged snapshot. `uv run --frozen pre-commit run --all-files` explicitly checks
the complete tracked tree. First tool-environment installation and vulnerability queries can
require network access; ordinary installed commit checks require no models, phone, or VM.
