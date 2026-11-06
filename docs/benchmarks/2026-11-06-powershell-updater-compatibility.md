# Windows updater module compatibility — 2026-11-06

This is local Windows PowerShell 5.1/Python 3.12.12 integration evidence, not physical-device,
GPU, audio, model-inference, package-deployment, or hosted-run acceptance.

## Remaining hosted failure

[Run 42230794616](https://github.com/R-zine/govor.ai/actions/runs/42230794616), source `d501371`,
passed Android, media, renderer, C#, and hygiene jobs. Python reached its test stage. The owner
provided its traceback: 395 passed, three updater cases failed, and coverage remained 85.60%.
All three failures originated at Get-Sha256 calling an unavailable Get-FileHash function.

The module-path mechanism is documented in the upstream
[PowerShell issue](https://github.com/PowerShell/PowerShell/issues/27774). A PowerShell 7 parent
can pass a module layout through Python that hides Windows PowerShell's script-based hash
function. This machine has Windows PowerShell 5.1; PowerShell 7 was not installed for this check.

## Reproduction and repair

The three existing updater integration cases now run with native and shadowed Utility module
layouts. The test-owned shadow manifest uses the actual Windows PowerShell cmdlet assembly,
explicitly advertises Get-FileHash as a cmdlet, and exports no script functions. Before exercising
the updater, a separate child-process probe confirms Add-Type works and Get-FileHash is absent.
This is a controlled compatibility fixture, not a substitute shell/runtime binary.

With the original verifier, the shadowed cases reproduced the same three missing-function
failures; the native cases passed. An initial wildcard-export fixture did not reproduce the
absence, so it was corrected to explicit exports and verified with the probe before relying on it.

Get-Sha256 now uses .NET's streaming SHA-256, lowercase hexadecimal output, and deterministic
stream/algorithm disposal. Signature, base hash, payload hash, staging, and rollback behavior
remain enforced. The success case also validates empty and 4 MiB arbitrary-binary payloads.
There are no new dependencies or weakened checks. This protected bootstrap change needs a full
release for existing installations; no installed host or phone application was changed.

## Verification

| Command | Result |
| --- | --- |
| `uv run --frozen pytest apps/launcher/tests/test_application_patch.py -k windows_updater -q --tb=short` before repair | Three native cases passed; three shadowed cases failed with the same missing Get-FileHash errors as CI |
| `uv run --frozen pytest apps/launcher/tests/test_application_patch.py -q --tb=short` after repair | 16 passed, including both layouts, rollback, and tamper rejection |
| Ruff check and format check on the changed Python test | Passed |
| `./scripts/check-powershell-syntax.ps1 distribution/windows/Apply-Govor-Patch.ps1` | Passed |
| `./scripts/test.ps1 -Scope python` with UV_PROJECT_ENVIRONMENT=.cache/ci-repair/python-minimal and PYTEST_ADDOPTS=--cov-report=xml | Passed: 401 tests, 85.60% branch coverage, XML coverage, Ruff/format, and 57-source strict mypy |
| Affected-test preview for the two changed implementation/test paths | Selects only apps/launcher/tests plus Python lint/types; no Android/Godot/media suites |

Ignored logs are `.cache/ci-repair/updater-regression-before.log`,
`updater-regression-after.log`, and `python-updater-fixed.log`. Existing Starlette and pytest-cache
warnings remain visible. The focused commit runs the final affected launcher and hygiene checks.
The next hosted run remains pending a push by the repository owner; it is not reported as green.
