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

Install the commit checks once per clone, then use focused changes:

```powershell
uv run --frozen pre-commit install --install-hooks
git add <changed-files>
./scripts/pre-commit-tests.ps1 -Staged -ListOnly
git commit
```

The hook selects staged component tests and their consumers, plus formatting, linting, static
types, syntax, and repository hygiene. Review and stage any automatic formatting corrections
before retrying. Deleted/renamed files are included; documentation-only changes skip application
tests. See [the selection rules](docs/development/commands.md). Run
`uv run --frozen pre-commit run --all-files` for an explicit complete repository check.

Run `./scripts/test.ps1 -Scope all` before marking a milestone acceptance criterion verified.
Hardware tests require their named hardware; do not replace them with mocks or emulators.

Never commit credentials, signing keys, model weights, raw learner recordings, private learning
history, or generated build artifacts. New runtime dependencies require a pinned version, license
review, rationale, and update to `THIRD_PARTY_LICENSES.md`.

Use synthetic examples in bug reports. Report vulnerabilities through the private route described
in [SECURITY.md](SECURITY.md). Before publishing a binary release, complete the
[release licensing review](distribution/OPEN_SOURCE_RELEASE.md); a passing build is not a license
clearance for bundled native libraries.
