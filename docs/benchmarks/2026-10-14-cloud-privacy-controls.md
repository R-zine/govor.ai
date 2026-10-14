# Milestone 7 cloud/privacy verification — 2026-10-14

## Scope and environment

Windows process build 10.0.26200 in the repository's pinned Python 3.12 environment. This is a
software/security verification record, not a cloud quality, latency, cost, or physical-hardware
benchmark. No real cloud service, paid account, learner recording, or learner transcript was used.

## Evidence

- Focused command: `uv run --frozen --extra speech pytest apps/host/tests services/local_ai/tests services/provider_router/tests packages/progress/tests -q`
- Result: 55 passed after correcting one invalid test scenario identifier.
- The mock transport verified strict structured dialogue, bearer-header placement, bounded STT WAV
  upload, WAV TTS output, null timing, and independent provider capabilities.
- The offline test constructed a cloud adapter and proved that its request handler was never called
  when the runtime policy was offline. Missing/rejected credentials raised typed failures. Sentinel
  credential, transcript, and response-body values were absent from captured logs.
- Full learner-data deletion removed all history and restored default settings. Existing history-
  only deletion continues to preserve explicit settings.
- A generated throwaway credential completed set/status/delete through the actual current-user
  Windows Credential Manager. The value was supplied on standard input, never displayed, and the
  credential was removed in the same `finally`-guarded check.
- The confirmation-gated `DeleteAll` CLI returned empty collections and default settings from a
  disposable database, which was removed after inspection.
- `./scripts/test.ps1 -Scope all` passed with 140 Python tests at 86.18% branch coverage, 13
  Kotlin tests, 8 C# tests, 15 media tests, Godot import/build/self-test, and Android debug build.
- The final pinned dependency audit reported no known vulnerabilities, and all configured
  pre-commit hooks passed across tracked and newly created files.
- The first full Python run passed all 134 then-current tests but missed the coverage gate at
  83.22%. CLI/store tests plus an explicit coverage exclusion for the separately smoke-tested thin
  Win32 FFI produced the final passing gate; invalid-credential host and streamed-response-limit
  regressions raised the count again without weakening coverage.

Final full-suite, audit, pre-commit, and Windows Credential Manager smoke results are recorded in
`docs/milestones/STATUS.md`; update this record if a later run changes the result.

## Limits

Mock compatibility tests do not prove that a specific vendor supports strict JSON schema, accepts
the exact multipart shape, emits supported mono PCM16 WAV, has acceptable latency, or follows a
particular retention policy. Those properties require explicit provider selection, provider terms
review, a non-production test account, and a separately authorized integration run.
