# GPL distribution materials

The Windows package contains unmodified GPL-3.0-or-later components used by the local speech
process: Piper 1.8.0, Phonemizer 3.4.0, and eSpeak NG 1.52 as carried by
`espeakng-loader==0.2.4`.

The package includes:

- the complete govor.ai source tree and build/package scripts as shipped for this version;
- checksum-pinned upstream source archives for each GPL component under
  `documentation/corresponding-source/upstream`; and
- the installed components' license files under `documentation/python-package-licenses`.

The components are distributed without warranty under their respective licenses. The upstream
archives are the preferred source snapshots corresponding to the pinned, unmodified components.
Model weights are separate data artifacts and their identifiers, checksums, revisions, and
licenses are listed in `config/release-models.json`.

This record documents the project's distribution materials; it is not legal advice.
