# Third-party dependency register

This file is a dependency review register, not a replacement for bundled license texts. Exact
resolved Python versions are in `uv.lock`; Gradle and NuGet versions are pinned in their project
files.

| Component | Version | Source | License | Redistribution note |
| --- | --- | --- | --- | --- |
| Python | 3.12.x | python.org | PSF-2.0 | Runtime packaging review required |
| FastAPI | 0.142.4 | github.com/fastapi/fastapi | MIT | Source notice required; upgraded after vulnerability audit |
| Pydantic | 2.11.9 | github.com/pydantic/pydantic | MIT | Source notice required |
| Uvicorn | 0.37.0 | github.com/encode/uvicorn | BSD-3-Clause | Retain notice |
| jsonschema | 4.25.1 | github.com/python-jsonschema/jsonschema | MIT | Source notice required |
| aiortc (Milestone 1 experiment) | 1.15.0 | github.com/aiortc/aiortc | BSD-3-Clause | Retain notice; transitive PyAV/FFmpeg codec licenses need packaging review |
| PyAV (Milestone 1 experiment) | 14.2.0 | github.com/PyAV-Org/PyAV | BSD-3-Clause | Chosen over 14.4.0 because 14.2.0 publishes a Windows CPython 3.12 wheel; bundled FFmpeg licenses need review |
| libwebrtc Android AAR (Milestone 1) | 150.7871.01 | github.com/webrtc-sdk/android | BSD-3-Clause plus bundled notices | Retain AAR third-party notices; maintained fork, not a Google Maven release |
| OkHttp | 4.12.0 | github.com/square/okhttp | Apache-2.0 | Retain notice |
| AndroidX / Jetpack Compose | pinned by Gradle catalog | developer.android.com | Apache-2.0 | Retain notices |
| xUnit.net | pinned by project | xunit.net | Apache-2.0 | Retain notice |
| Godot Engine .NET editor/export templates | 4.7.2 | github.com/godotengine/godot | MIT | Retain the Godot copyright and license notice in distributions; portable development artifacts are checksum-pinned |
| llama.cpp Windows Vulkan runtime | b11540 | github.com/ggml-org/llama.cpp | MIT | Repository-local development runtime is checksum-pinned; retain license notice if distributed |
| whisper.cpp Windows x64 runtime | b5454 | github.com/ggml-org/whisper.cpp | MIT | Repository-local development runtime is checksum-pinned; retain license notice if distributed |
| Qwen3-4B-GGUF model | revision `bc640142`, Q4_K_M | huggingface.co/Qwen/Qwen3-4B-GGUF | Apache-2.0 | 2.50 GB development model is checksum-pinned and ignored; distribution packaging remains a later review |
| Qwen3-1.7B-GGUF comparison model | revision `7fb011e9`, Q4_K_M | huggingface.co/Qwen/Qwen3-1.7B-GGUF | Apache-2.0 | 1.11 GB benchmark-only model is checksum-pinned and ignored; it is not the selected default |
| Whisper multilingual small model | revision `5359861c` | huggingface.co/ggerganov/whisper.cpp | MIT | 488 MB development model is checksum-pinned and ignored; distribution packaging remains a later review |
| whisper.cpp `jfk.wav` test recording | b5454 | github.com/ggml-org/whisper.cpp | MIT | Ignored, checksum-pinned human-speech test fixture; not packaged |
| VoxForge Bulgarian `dtd-20120908-cuf` recording | 2012-09-08 archive | repository.voxforge1.org | GPL-3.0-or-later | Ignored, checksum-pinned test fixture only; must not be bundled without GPL distribution review |

Model weights, voices, avatars, environment assets, and eSpeak/phonemizer components are not
distributed by this source repository. The two Milestone 3 development weights above are downloaded
to ignored local tooling storage; their redistributability must be reviewed again before packaging.
In particular, no GPL component may be bundled until its distribution implications are recorded.
