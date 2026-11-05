# Open-source preparation review — 2026-11-05

Scope: license/readme/documentation and package notice collation. Baseline: `79e693b` on the
Windows 10.0.26200 x64 development PC. No hardware/media acceptance, fresh Windows installation,
public repository creation/visibility change, or binary publication was performed.

## Findings and changes

- The original project had no `LICENSE`. Added the complete GPLv3 text, `COPYRIGHT` with an
  explicit GPL-3.0-or-later grant/scope, and matching README/contribution terms. Third-party code,
  model/voice artifacts, Gradle tooling, and the recorded CC0 assets retain their own terms.
- The root README now covers implemented features, practical learner setup for both devices,
  network/pairing, updates/data locations, developer prerequisites, mock and real-model emulator
  flows, tests, packaging/signing, architecture, and the MVP's known limits. Old milestone prose
  and the obsolete procedural-teacher description were removed from the introduction.
- The pinned `espeakng-loader` 0.2.4 wheel has no license declaration/text in its dist-info.
  However, the existing source archive at `0ddc87adf77e5850d7eeb542ac8a87d421b64daa` contains an
  MIT `LICENSE`, confirmed against that exact upstream file. Added its full notice under
  `licenses/third-party` and corrected the register/source-manifest description. This does not
  change the native eSpeak NG engine/data's GPL terms.
- The Windows packager now copies project `LICENSE`, `COPYRIGHT`, and the license-text directory
  to its root, plus the public-release review to its documentation. Existing 0.1.24 artifacts were
  not repackaged or modified by these source changes.
- Added security-reporting guidance and ignore rules for additional key, model, and SQLite
  formats. Updated agent/architecture/release guidance and ADR-0023 so a successful package build
  cannot be mistaken for a completed public redistribution review.

## Native media finding: public binary review is open

The earlier PyAV register entry described only the wrapper's BSD-3-Clause license. Actual local
PyAV 14.2.0 reports FFmpeg **7.1**. Calling the loaded codec DLL's `avcodec_license()` returns
**GPL version 3 or later**. Its configuration enables `--enable-gpl`, `--enable-version3`,
`--enable-libx264`, and `--enable-libx265`, without `--enable-nonfree` in the reported flags.

Measured library versions:

| Library | ABI version |
| --- | --- |
| libavutil | 59.39.100 |
| libavcodec | 61.19.100 |
| libavformat | 61.7.100 |
| libavdevice | 61.3.100 |
| libavfilter | 10.4.100 |
| libswscale | 8.3.100 |
| libswresample | 5.3.100 |

The development and packaged 0.1.24 `avcodec` DLL hashes match:
`febcda40fa119f3d3624c36cca285d62287e339597a81c611eb26f7de6b5f2f8`.
Full configuration and versions are in ignored `.cache/open-source-native-licenses.json`.
The wheel also contains codec and support DLLs including x264/x265, GMP, iconv, LAME, SRT,
OpenSSL, and compiler runtime libraries. Their complete corresponding source/build-input and
copyright/notice inventory was not established by the old four speech-source archives.

The existing Android release APK has one path containing `license`/`notice`/`copying`:
`okhttp3/internal/publicsuffix/NOTICE`. Its Gradle packaging also excludes `META-INF/LICENSE*`.
This filename inspection is not a complete byte-level license inventory, but the standalone APK
notice-delivery review cannot be considered complete from the Windows ZIP's WebRTC notices.

These are real remaining public-binary-release items, recorded in
`distribution/OPEN_SOURCE_RELEASE.md`. Adding the project's GPL license, including generic source
tarballs, or pointing to an upstream homepage alone does not resolve them. No license permission
was invented for a bundled component. Local builds and historical private deployment/hardware
evidence remain distinct from a public binary compliance claim.

## Privacy/history check

Downloaded Gitleaks 8.30.1 from its official release to ignored `.tools/gitleaks-8.30.1` and
verified the Windows x64 archive against that release's checksum file:
`d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e`.
This MIT-licensed audit tool is not an application dependency or shipped runtime.

Executed locally with command-scoped Git ownership configuration inherited by the child:

```powershell
./.tools/gitleaks-8.30.1/gitleaks.exe git --redact=100 --report-format json --report-path .cache/open-source-history-gitleaks.json --log-opts=--all .
```

Result: **exit 0, 40 available commits, about 2.66 MB scanned, no candidate secrets**, in 1.13 s.
The ignored report is `[]`. A historical tracked-path check for `.cache`, `.tools`, `.secrets`,
`.env`, recordings/data, keystores/PFX, model weights, SQLite files, and ISO images found no paths.
No files or Git history were deleted or rewritten. This bounded scan does not prove absence of
all private information or cover future/unavailable refs.

## Verification

- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .cache/check-open-source.ps1`:
  **passed**. Parsed all seven README PowerShell examples; executed the four actual new packager
  `Copy-Item` AST statements against disposable local staging; verified exact copied license hashes
  and the included release-review document.
- Local Markdown path check across README, contributing, security, license provenance, and public
  release review: **25 links passed**. External hyperlinks and whole fresh-environment workflows
  were not treated as executed setup evidence.
- `python -m json.tool config/release-sources.json`: **passed**; only the loader's license
  description changed, with no dependency version, artifact digest, or download change.
- `./scripts/check-powershell-syntax.ps1 scripts/package.ps1`: **passed**.
- `./scripts/test.ps1 -Scope all`: **exit 0**; 356 Python tests at 85.63% branch coverage, Kotlin
  core/app tests, 13 C# tests, 21 real aiortc media tests, Godot import/build/headless self-test,
  and debug APK assembly passed. Ruff/format and strict mypy passed. Existing Starlette
  deprecation and ignored pytest-cache access warnings remain nonfatal. Log:
  `.cache/open-source-full-tests.log`.
- The focused commit also runs the installed hygiene, contract, and affected-application hooks.
  `COPYRIGHT` selects the complete software gate under the current path dispatcher. Its log is
  `.cache/open-source-commit.log`. The exact staged diff also passed Gitleaks with **exit 0**, no
  candidate secrets; reports stay under ignored `.cache` as
  `open-source-staged-gitleaks.json` and `.log`.

No application/model listeners on ports 8765-8768 remained after the full suite. No new physical
phone behavior, fresh clone/setup, model download, or public binary package was verified here.

The first native inspection attempted the newer `av.library_meta` API, which is absent in PyAV
14.2.0. The corrected inspection used the actual DLL's exported licensing/configuration functions
and `av.ffmpeg_version_info`. Several GNU/raw-source web fetches timed out; the complete
GPL text came from the pinned Piper `COPYING` with line endings and terminal blank lines normalized for the
whitespace gate, and the missing wrapper notice came from the
already checksum-pinned source archive. These retrieval failures are not counted as passing tests.

The first commit attempt's whitespace gate normalized the copied GPL document's mixed line
endings. The affected complete software gate passed in that attempt; the commit was correctly
rejected until the formatting fix was included and the required hooks rerun. The license wording
was not changed.

## Primary references

- [GNU project licensing guidance](https://www.gnu.org/licenses/gpl-howto.en.html) and
  [GPL combination/source FAQ](https://www.gnu.org/licenses/gpl-faq.en.html).
- [PyAV wrapper license](https://github.com/PyAV-Org/PyAV/blob/v14.2.0/pyproject.toml),
  [FFmpeg licensing](https://ffmpeg.org/legal.html), and
  [PyAV native build tooling](https://github.com/PyAV-Org/pyav-ffmpeg).
- [Exact eSpeak loader MIT notice](https://github.com/thewh1teagle/espeakng-loader/blob/0ddc87adf77e5850d7eeb542ac8a87d421b64daa/LICENSE).
- The four current Wikimedia file-description pages linked in
  `apps/renderer/Assets/Backdrops/README.md` explicitly state CC0; the living-room page records the
  pre-2017 Unsplash dedication. Teacher provenance remains recorded beside the exact GLBs.
