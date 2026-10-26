# Third-party dependency register

This file is a dependency review register, not a replacement for bundled license texts. Exact
resolved Python versions are in `uv.lock`; Gradle and NuGet versions are pinned in their project
files.

| Component | Version | Source | License | Redistribution note |
| --- | --- | --- | --- | --- |
| Python | 3.12.x | python.org | PSF-2.0 | Embedded runtime; retain Python license and bundled notices |
| Microsoft Visual C++ Redistributable x64 | 14.51.36247.0 | download.visualstudio.microsoft.com | Microsoft Software License Terms | Not embedded in the ZIP; guided setup downloads Microsoft's signed installer directly, verifies exact size/SHA-256 plus Authenticode signer, and installs it centrally when the packaged llama runtime cannot load |
| certifi | 2026.10.19 | github.com/certifi/python-certifi | MPL-2.0 | Pinned CA bundle used by release/runtime HTTPS; installed-package license is bundled |
| cryptography | 50.0.2 | github.com/pyca/cryptography | Apache-2.0 OR BSD-3-Clause | Release TLS identity generation; installed-package licenses are bundled |
| FastAPI | 0.142.4 | github.com/fastapi/fastapi | MIT | Source notice required; upgraded after vulnerability audit |
| Pydantic | 2.11.9 | github.com/pydantic/pydantic | MIT | Source notice required |
| Uvicorn | 0.37.0 | github.com/encode/uvicorn | BSD-3-Clause | Retain notice |
| jsonschema | 4.25.1 | github.com/python-jsonschema/jsonschema | MIT | Source notice required |
| aiortc media gateway | 1.15.0 | github.com/aiortc/aiortc | BSD-3-Clause | Installed-package license is bundled with the release runtime |
| PyAV media dependency | 14.2.0 | github.com/PyAV-Org/PyAV | BSD-3-Clause | Chosen because it publishes a Windows CPython 3.12 wheel; installed metadata/licenses are bundled |
| libwebrtc Android AAR | 150.7871.01 | github.com/webrtc-sdk/android | BSD-3-Clause plus bundled notices | Exact wrapper license and WebRTC third-party notice set are bundled from commit `7b6390fb` |
| OkHttp | 4.12.0 | github.com/square/okhttp | Apache-2.0 | Retain notice |
| AndroidX / Jetpack Compose | pinned by Gradle catalog | developer.android.com | Apache-2.0 | Retain notices |
| ZXing Android Embedded | 4.3.0 | github.com/journeyapps/zxing-android-embedded | Apache-2.0 | Offline QR camera/scanner activity; retain notice |
| ZXing Core | 3.4.1 (transitive) | github.com/zxing/zxing | Apache-2.0 | QR decoding used only on-device; retain notice |
| xUnit.net | pinned by project | xunit.net | Apache-2.0 | Retain notice |
| Godot Engine .NET editor/export templates | 4.7.2 | github.com/godotengine/godot | MIT | Release ships only the exported player; exact Godot license/copyright notices are hash-pinned and bundled |
| Ara 3D Gen build tooling | commit `0c3473d` | github.com/olatunde85/3d-gen | MIT | Build-time only; generator source and optional animation library are not bundled |
| Ara/MakeHuman teacher character data | September 2020 CC0 release | github.com/olatunde85/3d-gen; makehumancommunity.org | CC0-1.0 | Three generated GLBs are bundled; inputs, hashes, attribution, and animation-stripping step are recorded beside the assets |
| Built-in photographic backdrops | repository copies dated 2026-10-26 | commons.wikimedia.org | CC0-1.0 | Four 1280-pixel-wide JPEG derivatives are bundled; source pages, authors, and exact hashes are recorded in `Assets/Backdrops/README.md` |
| QEMU clean-Windows test fixture | 11.0.50 | qemu.org | GPL-2.0-only | System-installed development/test tool; not copied into either release artifact |
| llama.cpp Windows Vulkan runtime | b11540 | github.com/ggml-org/llama.cpp | MIT | Distributed runtime is pinned; exact license plus LLVM OpenMP license are bundled |
| whisper.cpp Windows x64 runtime | b5454 | github.com/ggml-org/whisper.cpp | MIT | Distributed runtime is pinned; exact license is bundled |
| Qwen3-4B-GGUF model | revision `bc640142`, Q4_K_M | huggingface.co/Qwen/Qwen3-4B-GGUF | Apache-2.0 | 2.50 GB model is installed separately by the guided setup only after exact size/SHA-256 verification |
| Qwen3-1.7B-GGUF comparison model | revision `7fb011e9`, Q4_K_M | huggingface.co/Qwen/Qwen3-1.7B-GGUF | Apache-2.0 | 1.11 GB benchmark-only model is checksum-pinned and ignored; it is not the selected default |
| Whisper multilingual small model | revision `5359861c` | huggingface.co/ggerganov/whisper.cpp | MIT | 488 MB model is installed separately by the guided setup only after exact size/SHA-256 verification |
| whisper.cpp `jfk.wav` test recording | b5454 | github.com/ggml-org/whisper.cpp | MIT | Ignored, checksum-pinned human-speech test fixture; not packaged |
| VoxForge Bulgarian `dtd-20120908-cuf` recording | 2012-09-08 archive | repository.voxforge1.org | GPL-3.0-or-later | Ignored, checksum-pinned test fixture only; must not be bundled without GPL distribution review |
| kokoro-onnx | 0.6.1 | github.com/thewh1teagle/kokoro-onnx | MIT | Local adapter; installed-package license is bundled |
| Kokoro v1.0 ONNX model and voices | release `model-files-v1.1` | github.com/thewh1teagle/kokoro-onnx | Apache-2.0 | Installed separately by guided setup with exact size/SHA-256 verification |
| piper-tts | 1.8.0 | github.com/OHF-Voice/piper1-gpl | GPL-3.0-or-later | Distributed with installed license, shipped govor.ai source, and pinned upstream source archive |
| Piper `bg_BG-dimitar-medium` voice | revision `7c89b592` | huggingface.co/rhasspy/piper-voices | CC0-1.0 dataset/model card; engine GPL applies separately | Model/config are installed separately with exact size/SHA-256 verification |
| phonemizer | 3.4.0 | github.com/bootphon/phonemizer | GPL-3.0-or-later | Distributed with installed license, shipped govor.ai source, and pinned upstream source archive |
| Segno | 1.6.6 | github.com/heuer/segno | BSD-3-Clause | Pure-Python release pairing QR encoder; installed-package license is bundled |
| espeakng-loader / bundled eSpeak NG | 0.2.4 / 1.52.0 library | pypi.org/project/espeakng-loader, github.com/espeak-ng/espeak-ng | Loader wheel metadata does not declare a wrapper license; bundled eSpeak NG is GPL-3.0-or-later | Conservatively distributed with installed notices and pinned source archives for loader and eSpeak NG |

Model weights and voices are not embedded in the portable archive; the guided setup downloads the
exact artifacts listed in `config/release-models.json`. The current teacher GLBs and photographic
backdrops are bundled CC0 assets with provenance, build inputs, and exact hashes under
`apps/renderer/Assets/Teacher` and `apps/renderer/Assets/Backdrops`. Installed custom environments
remain application-authored data-only primitive recipes.

The release archive includes installed Python package licenses, exact hash-pinned runtime notices,
the complete govor.ai source shipped for that version, and the upstream source snapshots listed in
`config/release-sources.json`. `distribution/GPL-COMPLIANCE.md` explains the layout. This register
and those materials document the current packaging decision; they are not legal advice.
