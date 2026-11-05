# ADR-0023: License original project material and distinguish binary release obligations

- Status: accepted for source licensing/documentation; public binary review remains open
- Date: 2026-11-05
- Scope: post-milestone open-source preparation

## Context

The owner requested open-source preparation and a readable README covering features, learner
installation, and local development. The repository had dependency notices and shipped source
snapshots, but no license grant for its original material. Its Windows speech process imports
GPL libraries. Its PyAV dependency register also omitted the GPL FFmpeg/codec binaries bundled
inside the actual Windows wheel.

## Decision

License original project source, scripts, documentation, tests, and lesson definitions under
**GPL-3.0-or-later**. Supply the complete unchanged GPLv3 text in `LICENSE`, with the explicit
or-later grant/scope/copyright notice in `COPYRIGHT` and contribution terms in `CONTRIBUTING.md`.
Keep upstream licenses and CC0/model terms intact. This is the project's selected grant, not a
claim that every separate process is automatically one GPL combined work.

The packager carries those license files and the copied pinned eSpeak loader MIT notice into
future portable packages. The source archive/license contents and private signing identities
remain separate. The README documents current implemented behavior and its MVP limits rather
than presenting milestone history as user instructions.

Treat source publication and public binary redistribution as distinct reviews. The measured
FFmpeg DLL reports GPL version 3 or later with GPL/version3/x264/x265 enabled. Exact native
sources/build inputs/dependency notices and standalone Android notice delivery must be closed
before public binary publication. Record these remaining items in
`distribution/OPEN_SOURCE_RELEASE.md`; do not infer compliance from a passing package build,
the PyAV wrapper's BSD license, or generic source tarballs. No dependency is replaced by this
documentation/license change, and no private key, repository visibility, remote, or release is
published.

## Consequences and evidence

The source has an explicit recognized open-source grant. A future permissive-only distribution
would require a separate dependency/combination review; simply renaming the host bundle's license
to MIT would not remove the existing GPL dependency obligations.

The exact eSpeak loader source archive includes its MIT notice despite missing wheel metadata.
Original code does not relicense that wrapper, bundled eSpeak NG, or the recorded CC0 artwork.
Local Gitleaks scanned all 40 available commits without candidate secrets; ignored-state and
historical path checks found no tracked private runtime files. This is bounded scan evidence,
not proof against every possible private-data disclosure. Tests, source checks, and limits are
recorded in `docs/benchmarks/2026-11-05-open-source-readiness.md`.
