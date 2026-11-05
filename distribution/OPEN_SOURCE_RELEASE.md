# Source publication and binary release review

Reviewed 2026-11-05. Original project material is **GPL-3.0-or-later** under `LICENSE` and
`COPYRIGHT`. Upstream dependencies/assets retain their own terms. This is a recorded engineering
review, not a claim that every dependency or jurisdiction has been legally cleared.

## Source repository

The repository now has the complete GPLv3 text, an explicit or-later grant, contribution terms,
human-oriented user/developer instructions, and a dependency/asset register. Models, private
signing keys, runtime credentials, learner history, and recordings must remain outside Git.

The 2026-11-05 local Gitleaks 8.30.1 scan covered all 40 available commits and found no candidate
secrets. A separate historical path check found no tracked signing keystores, `.secrets`, `.env`,
recordings, or learner databases. These checks have limits; repeat them on the exact branch/tag
and inspect any additional refs before making a repository public. No history was rewritten and
no repository visibility, remote, or release publication was changed by this review.

The reviewed GLBs retain their recorded CC0 MakeHuman provenance and contain no optional Ara
animation clips. The four backdrop source pages explicitly identify CC0, including the living
room photo's pre-June-2017 Unsplash dedication. Preserve those notices/provenance when forking.

## Binary publication remains pending

**Do not present the existing portable ZIP/APK or the packager as fully cleared for public binary
redistribution.** Local builds and the earlier private development deployments remain separate
from this public-release review. Build success and a valid APK signature are not license checks.
Conveying binaries to another person, including a private recipient, can also require source and
notices; an unpublished download is not a general exemption. These findings concern distributing
the bundle, not merely running it on the owner's own devices.

| Item | Finding | Required action before public binary publication |
| --- | --- | --- |
| Original project grant | Previously absent; now GPL-3.0-or-later | Include root `LICENSE`, `COPYRIGHT`, and the exact source/build scripts for the shipped version |
| Piper / Phonemizer / eSpeak NG | GPL-3.0-or-later; source snapshots already listed in `config/release-sources.json` | Verify the exact built native libraries, source/data/build inputs, license texts, and usable build instructions match what is shipped; source archive presence alone is not a complete inventory |
| eSpeak loader wrapper | The 0.2.4 wheel omits its license, but pinned source commit `0ddc87ad` contains MIT | Resolved attribution: retain `licenses/third-party/espeakng-loader-LICENSE.txt`; eSpeak NG itself stays GPL |
| PyAV wrapper and bundled FFmpeg/codecs | Wrapper BSD-3-Clause; actual Windows FFmpeg DLL reports GPL version 3 or later with GPL/version3/x264/x265 enabled | Obtain and pin the exact native source, patches, build scripts/configuration, codec/runtime dependency inventory, and required license/copyright notices, or replace the wheel with a reproducibly built distribution whose source/notices are complete |
| Standalone Android APK | Host-side WebRTC notices are bundled separately; Android packaging excludes `META-INF/LICENSE*` | Audit every packaged Android/native dependency; deliver its full applicable notices with the APK, plus exact matching GPL application source/build instructions. Do not assume notices in a separate Windows ZIP reach an APK-only recipient |
| Models and voices | Separate downloads, licensed independently of the application | Keep pinned revisions/digests and model cards/licenses. Recheck terms when changing a model or voice; the application GPL grant does not cover them |

The measured FFmpeg build configuration and library ABI versions are recorded in
`docs/benchmarks/2026-11-05-open-source-readiness.md`. The old register's PyAV BSD-only entry and
the earlier four GPL source archives do **not** cover the entire native media stack. In
particular, a generic FFmpeg release tarball or an upstream homepage is not evidence that it is
the complete corresponding source for the actual wheel and all its bundled dependencies.

## Maintainer release procedure

1. Close and record the native-source and standalone-APK notice items above before uploading
   public binaries. Keep an exact source snapshot with the binaries and the necessary build and
   installation information; comply with GPL section 6 and any applicable installation duties.
2. Build from a clean, reviewed checkout. Keep `.secrets`, model caches, progress, recordings, VM
   disks/ISOs, and local imported/generated lessons out of public artifacts and source snapshots.
3. Retain dependency notices and original asset terms. Inspect the final ZIP and APK/companion
   materials rather than relying only on dependency metadata or the source tree.
4. Publish version-matched artifacts, checksums, source materials, known limitations, and user
   instructions together. Keep private signing keys and OS pairing identity private. A fork must
   generate its own keys; publishing source does not require releasing the maintainer's keys.
5. Check current Android installation/developer-verification requirements for the intended
   distribution route and region. Do not promise installation on every Android device.

Primary references:

- [GNU licensing guidance](https://www.gnu.org/licenses/gpl-howto.en.html) and
  [GPL combination/source FAQ](https://www.gnu.org/licenses/gpl-faq.en.html).
- [FFmpeg licensing and distribution requirements](https://ffmpeg.org/legal.html).
- [PyAV 14.2 wrapper license declaration](https://github.com/PyAV-Org/PyAV/blob/v14.2.0/pyproject.toml)
  and [upstream FFmpeg build tooling](https://github.com/PyAV-Org/pyav-ffmpeg).
- [Pinned eSpeak loader MIT notice](https://github.com/thewh1teagle/espeakng-loader/blob/0ddc87adf77e5850d7eeb542ac8a87d421b64daa/LICENSE).
- [Asset provenance](../apps/renderer/Assets/Backdrops/README.md),
  [teacher provenance](../apps/renderer/Assets/Teacher/Ara/README.md), and
  [Android distribution guidance](https://developer.android.com/developer-verification).
