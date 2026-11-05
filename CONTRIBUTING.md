# Contributing

Start with the [README](README.md) for user installation, local development, and supported
features. For a code change, read the relevant architecture/decision records and current
`docs/milestones/STATUS.md`. The authoritative product requirements are in `docs/MASTER_SPEC.md`;
coding agents also follow `AGENTS.md`. Keep domain logic independent of frameworks and validate
every cross-process message against a versioned contract.

Contributions to original project code, documentation, tests, and lesson definitions are made
under **GPL-3.0-or-later**, the license in [COPYRIGHT](COPYRIGHT) and [LICENSE](LICENSE).
Contributors retain their copyright. Do not submit third-party code or assets without their
license, provenance, and redistribution terms. Existing CC0/upstream exceptions remain separate.

Use focused changes and run:

```powershell
./scripts/test.ps1 -Scope fast
uv run --frozen pre-commit run --all-files
```

Run `./scripts/test.ps1 -Scope all` before marking a milestone acceptance criterion verified.
Hardware tests require their named hardware; do not replace them with mocks or emulators.

Never commit credentials, signing keys, model weights, raw learner recordings, private learning
history, or generated build artifacts. New runtime dependencies require a pinned version, license
review, rationale, and update to `THIRD_PARTY_LICENSES.md`.

Use synthetic examples in bug reports. Report vulnerabilities through the private route described
in [SECURITY.md](SECURITY.md). Before publishing a binary release, complete the
[release licensing review](distribution/OPEN_SOURCE_RELEASE.md); a passing build is not a license
clearance for bundled native libraries.
