# Deployment architecture

Development uses repository-local Python, Gradle, NuGet, .NET, Godot, model, and runtime caches.
Those tools are inputs to packaging; they are not prerequisites for a learner.

## Windows portable distribution

`scripts/package.ps1` exports the Godot 4.7.2 player and stages a versioned Windows x64 directory:

```text
govor.ai-<version>-windows-x64/
|-- Install-Prerequisites.ps1
|-- Setup-Govor.cmd
|-- Start-Govor.cmd
|-- app/                 application source used by the embedded runtime
|-- config/              pinned model/source/notice manifests
|-- renderer/            exported Godot player, not the editor
|-- runtime/
|   |-- python/          embedded CPython and hash-locked dependencies
|   |-- llama.cpp/
|   `-- whisper.cpp/
`-- documentation/      guides, notices, and corresponding source
```

Updater-capable packages also contain `Apply-Govor-Patch.cmd`/`.ps1`, signed-release metadata, and
the public half of the dedicated application-update identity. The corresponding private RSA-3072
key remains beside the Android keystore in ignored, ACL-restricted `.secrets`.

The launcher stores mutable state under `%LOCALAPPDATA%\govor.ai`, never inside that versioned
directory:

```text
%LOCALAPPDATA%\govor.ai/
|-- models/              separately downloaded, size/SHA-256 verified artifacts
|-- progress/            SQLite settings and structured learning history
|-- security/            TLS private key/certificate and hashed gateway credentials
`-- logs/                redacted service logs
```

This split lets an update replace the portable directory without replacing models, progress, or
paired-device state. `Setup-Govor.cmd` checks the package and first proves the packaged llama
runtime can load. When the Microsoft Visual C++ runtime is absent, its helper downloads Microsoft's
versioned x64 redistributable directly, requires the pinned byte size and SHA-256 plus a valid
Microsoft Authenticode signature, and installs it centrally. Setup then downloads missing model
artifacts and atomically promotes them only after both the manifest size and SHA-256 match. Internet
is required for that setup only; `Start-Govor.cmd` forces local providers and `offline_only=true`.

The launcher starts llama.cpp on loopback, then the authenticated HTTPS/WSS media and control
gateways, then the exported renderer. Local model/capture traffic stays on loopback. A Windows Job
Object and an explicit reverse-order stop path ensure launcher exit closes every child even if a
child ignores the first termination request.

## LAN and Android distribution

The Windows gateway binds ports 8765 (control/pairing) and 8766 (media signaling) to the LAN. On
first run, the launcher creates a current-user self-signed TLS identity and a temporary QR with
the selected endpoints, its SHA-256 fingerprint, and an eight-digit, ten-minute, one-time pairing
code. The QR is shown locally by Godot outside the streamed scene. The Android release APK scans
the bootstrap on-device, pins the fingerprint, exchanges the code over HTTPS, encrypts its random
device credential with Android Keystore, and authenticates later HTTPS/WSS requests with that
credential. The console and a collapsed Android section retain manual pairing for diagnostics.
WebRTC media uses DTLS-SRTP.

### Mixed Ethernet/Wi-Fi topology assessment

The gateway already listens on all IPv4 interfaces, uses interface-independent HTTPS/WSS
addresses, and lets WebRTC gather host candidates, so a Windows PC on wired Ethernet and a phone
on Wi-Fi need no wire-contract or lesson/media redesign when both links reach the same trusted
private LAN. The current launcher, however, advertises one sorted hostname-resolved IPv4 address.
That is insufficient for a multi-homed PC because the first address may belong to an isolated,
VPN, virtual, disconnected, or Windows Public-profile interface.

A separate topology change should enumerate active physical adapters with their prefix/gateway and
Windows network category, exclude loopback/link-local/virtual or Public-profile candidates by
default, and either select the route that can reach the phone subnet or present the bounded
private candidates for the user to choose. It must keep firewall rules restricted to the Private
profile, test TCP 8765/8766 and ICE across the Ethernet-to-access-point path, and document router
client isolation/VLAN failure modes. QR pairing can then encode the selected reachable address.
This assessment does not claim that deterministic multi-adapter selection is implemented.

The release APK has application ID `ai.govor.app`, monotonically increasing `versionCode`, a
human-readable version name, and a stable user-controlled RSA-3072 signing identity. Signing state
is excluded from Git and distribution artifacts. Compatible updates require the same key.

For an incremental release, `scripts/create-application-patch.ps1` compares a retained base
package with the new package and signs a `.govorpatch`. The installed bootstrap checks the exact
base and payload, performs a transactional local update, and preserves unlisted files. If the
patch includes the new release APK, it is verified and saved for explicit transfer/opening on the
phone; the updater never uses ADB or bypasses Android confirmation. A pre-updater package must be
replaced once with a complete updater-capable release.

`scripts/package.ps1` verifies the APK signature and creates an artifact manifest with byte sizes
and SHA-256 digests. It also bundles exact runtime notices, installed Python package licenses, the
shipped govor.ai source, and pinned GPL upstream source archives. ADR-0011 records this decision.

## Local clean-Windows acceptance fixture

Milestone 8 uses a persistent QEMU/WHPX Windows 11 x64 base under ignored `.cache/m8-vm`. The
caller supplies the test ISO and its independently recorded SHA-256, which is verified before boot.
The fixture records but does not certify image provenance, activation, or licensing, and the image
is never distributed with govor.ai. Provisioning installs only the test-control OpenSSH server and
creates no govor.ai application state. Each acceptance attempt runs in a new qcow2 overlay over
that stopped base; resetting an attempt requires the explicit `ResetRun -ConfirmReset` action.

QEMU user-mode networking exposes SSH only at host loopback port 55222. Guest control/media ports
8765/8766 are forwarded to host loopback ports 18765/18766; one M8-only ICE UDP port is forwarded
at 18770. The host Android emulator reaches those ports through its `10.0.2.2` host alias, so no
nested emulator or `adb reverse` is involved. The explicit ICE candidate substitution is enabled
only by fixture environment variables and leaves ordinary release LAN behavior unchanged.
See ADR-0012 and `docs/testing/m8-clean-vm.md` for the trust and evidence boundaries.

## Evidence boundary

The packaged stack, authenticated release APK, persistent credential, complete café lesson, update
from version code 1 to 2, and clean shutdown executed on the API 34 emulator without `adb reverse`.
The final 0.1.4 package also completed setup/start/media/shutdown in a Windows 10.0.22000.0 AMD64
QEMU/WHPX guest using the host emulator. That closes Milestone 8's clean-software row for the exact
recorded image. The intended physical phone, Wi-Fi path, firewall behavior, codecs, audio hardware,
target performance, lifecycle, monitor-off behavior, thermals, and bounded stability are distinct
Milestone 9 checks and are not inferred from the VM/emulator run. They later passed separately on
the documented target PC, physical phone, and intended private Wi-Fi.
