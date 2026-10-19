# ADR-0012: Local clean-Windows acceptance fixture

- Status: accepted; acceptance execution verified
- Date: 2026-10-17
- Verified: 2026-10-19
- Milestone: 8

## Context

Milestone 8 requires a clean Windows system to install and launch the portable release using the
documented entry points. The development host cannot prove that property. The first independent
0.1.1 attempt correctly exposed a batch-wrapper defect; 0.1.2 fixed it, but no reusable clean
environment was available for the retry. Windows Sandbox is unavailable in the current account,
and placing an Android emulator inside a Windows VM would add unsupported nested virtualization.

The host already has QEMU 11.0.50 with the Windows Hypervisor Platform accelerator, 31.8 GiB of
RAM, sufficient free disk, OpenSSH clients, and the API 34 Android Studio emulator.

## Decision

Use `scripts/m8-vm.ps1` and `config/m8-vm.json` to manage a Windows 11 x64 guest on QEMU/WHPX. The
user supplies the test ISO and an independently recorded SHA-256. The fixture verifies that digest
before creating VM state but does not certify image provenance, activation, or licensing. The
project does not download, redistribute, activate, or bypass licensing for the image. Microsoft's
evaluation download remains the documented reference source, not an enforced provenance claim.

Provisioning creates a 96 GiB sparse qcow2 base with 8 GiB RAM, four virtual CPUs, persistent EDK2
UEFI variables, QEMU user-mode networking, and a random local administrator password. Generated
unattended material, the DPAPI-protected password, SSH key, disks, logs, and evidence remain under
ignored `.cache/m8-vm`, whose ACL is restricted to the current user and SYSTEM. The guest installs
OpenSSH Server, accepts only the generated administrator public key, and restricts its SSH
firewall rule to the Private profile.

After provisioning stops, the base disk and base UEFI variables are never booted for an
acceptance attempt. `Start` creates a qcow2 overlay and copied UEFI variable store. `ResetRun`
requires `-ConfirmReset`, refuses to run while QEMU is active, validates every deletion target is
inside the fixture root, and discards only that mutable layer and its host-side run evidence.

Network mappings are fixed and explicit:

| Purpose | Guest | Host loopback | Android emulator |
| --- | --- | --- | --- |
| Test control | TCP 22 | `127.0.0.1:55222` | not exposed to the app |
| Release control/WSS | TCP 8765 | `127.0.0.1:18765` | `10.0.2.2:18765` |
| Release media/WSS | TCP 8766 | `127.0.0.1:18766` | `10.0.2.2:18766` |
| M8 ICE fixture | UDP 18770 | `127.0.0.1:18770` | `10.0.2.2:18770` |

`StageRelease` first requires the host ZIP/APK to match the artifact manifest, then copies only the
Windows ZIP, signed APK, and manifest. The guest re-hashes all three files and checks that the
manifest still describes the ZIP/APK before extraction. `SetupRelease` crosses the packaged
`Setup-Govor.cmd` boundary. `StartRelease` crosses `Start-Govor.cmd`, uses its bounded internal
smoke duration, and opens the two Python gateway ports plus the single fixture ICE UDP port on the
guest Private profile.
`WaitRelease` requires zero release listeners and zero package-owned processes and retrieves JSON
shutdown evidence.

QEMU user networking does not make a guest host ICE candidate reachable from the host emulator.
For this fixture only, environment variables select a validated private advertise address and a
fixed UDP bind port. The media service substitutes that single host candidate while retaining WSS
signaling and DTLS-SRTP. Without those variables the adapter is inactive and normal release LAN
candidate behavior is unchanged.

The Android Studio emulator remains on the host. It connects through QEMU's loopback forwards and
must have no `adb reverse` mapping. This avoids nested virtualization and tests the signed app
against the clean guest's actual authenticated gateway.

## Evidence boundary and risks

- A passing run may satisfy only the Milestone 8 clean-Windows install/launch row. A VM is a clean
  software environment, not the target Windows hardware.
- The host Android emulator remains emulator evidence. It cannot satisfy physical installation,
  Wi-Fi, acoustic, codec, lifecycle, latency/resource, monitor-off, thermal, or soak requirements.
  Those stay mandatory in Milestone 9.
- This QEMU configuration has no virtual TPM or Secure Boot and exposes a generic virtual CPU. The
  unattended fixture uses Windows Setup registry compatibility switches for those three virtual-
  hardware checks. This is a test-fixture limitation, not release guidance or target-machine
  evidence.
- QEMU standard VGA did launch the exported Godot renderer and published non-black frames in the
  recorded run. This does not establish target GPU performance, hardware encoding, or monitor-off
  behavior.
- Image provenance/activation and Windows Update state must be recorded with the run. The base contains no
  application models, developer checkout, Python, Godot editor, Android tooling, or prior
  govor.ai state.

## Verification

The 2026-10-19 run used a 4,693,557,248-byte user-supplied image with SHA-256
`15fecff356411d43c77df040e1847427402b0e09da069bf1db0cb754932075b9`. The project did not
independently verify its provenance, activation, or license and does not distribute it. The guest
reported Windows 10.0.22000.0 AMD64. The final 0.1.4 package passed exact wrapper setup, six-model
status, authenticated host-emulator connection without `adb reverse`, non-black Godot video,
nonzero Godot PCM, emulator microphone return, and clean bounded shutdown. Details and transient
failures are in `docs/benchmarks/2026-10-19-m8-clean-vm-acceptance.md`.

## Rejected

- Treating the development host or package-generation smoke as a clean system.
- Treating Windows Sandbox status, compilation, or an unbooted VM image as execution evidence.
- Running a nested Android emulator in the guest.
- Exposing SSH or forwarded application ports on a non-loopback host interface.
- Accepting an ISO without recording/verifying its exact digest, redistributing it, or automating
  activation/licensing bypass.
- Using this VM/emulator result to close any Milestone 9 hardware row.
