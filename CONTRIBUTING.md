# Contributing

Read `AGENTS.md`, `docs/MASTER_SPEC.md`, `docs/milestones/STATUS.md`, and the relevant ADRs before
changing code. Keep domain logic independent of frameworks and validate every cross-process
message against a versioned contract.

Use focused changes and run:

```powershell
./scripts/test.ps1 -Scope fast
uv run pre-commit run --all-files
```

Run `./scripts/test.ps1 -Scope all` before marking a milestone acceptance criterion verified.
Hardware tests require their named hardware; do not replace them with mocks or emulators.

Never commit credentials, signing keys, model weights, raw learner recordings, private learning
history, or generated build artifacts. New runtime dependencies require a pinned version, license
review, rationale, and update to `THIRD_PARTY_LICENSES.md`.
