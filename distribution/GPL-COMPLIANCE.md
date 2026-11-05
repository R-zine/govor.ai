# GPL distribution materials

Original project material is GPL-3.0-or-later under the root `LICENSE` and `COPYRIGHT`.
The existing distribution materials below are **not a complete public-binary clearance**.
The 2026-11-05 review found additional GPL FFmpeg/codecs in the PyAV Windows wheel and a
standalone-APK notice-delivery gap. See `OPEN_SOURCE_RELEASE.md` for the required remaining work.

The Windows package contains unmodified GPL-3.0-or-later components used by the local speech
process: Piper 1.8.0, Phonemizer 3.4.0, and eSpeak NG 1.52 as carried by
`espeakng-loader==0.2.4`.

The package includes:

- the complete govor.ai source tree and build/package scripts as shipped for this version;
- checksum-pinned upstream source archives for each GPL component under
  `documentation/corresponding-source/upstream`; and
- the installed components' license files under `documentation/python-package-licenses`.

The packager also copies the project `LICENSE`, `COPYRIGHT`, and `licenses` directory to the
portable package root. The eSpeak loader wrapper's pinned upstream MIT notice is included there
because the wheel's metadata omits it. Its native eSpeak NG library/data remains separately GPL.

The components are distributed without warranty under their respective licenses. The upstream
archives are source snapshots for the pinned components, but do not by themselves establish that
all native build inputs, transitive libraries, and corresponding-source obligations are covered.
Model weights are separate data artifacts and their identifiers, checksums, revisions, and
licenses are listed in `config/release-models.json`.

This record documents the project's distribution materials; it is not legal advice.
