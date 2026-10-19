# Milestone 8 local VM fixture evidence

> Historical pre-execution record. The exact clean-VM acceptance run passed on 2026-10-19 and is
> recorded in `2026-10-19-m8-clean-vm-acceptance.md`. The blocked status below describes only the
> 2026-10-17 checkpoint.

- Date: 2026-10-17
- Time zone: Europe/Kyiv
- Scope: clean-Windows fixture implementation and host capability only
- Acceptance status: **blocked / not executed**

## Host inventory

- Windows development host: process build 10.0.26200
- Memory: 31.8 GiB total; approximately 16 GiB available during discovery
- System drive: approximately 461.9 GiB free
- QEMU: 11.0.50 (`v11.0.0-12631-g54e84cdc7a`)
- QEMU accelerators reported: `tcg`, `whpx`
- OpenSSH client: `ssh.exe`, `scp.exe`, and `ssh-keygen.exe` present
- Android fixture: existing API 34 Android Studio emulator on the host; no nested emulator planned
- Official Windows evaluation ISO: not present

## Implemented fixture

`scripts/m8-vm.ps1`, `config/m8-vm.json`, and the two templates under `distribution/vm` now define
a QEMU/WHPX Windows 11 Enterprise evaluation fixture. The host ports bind only on loopback. SSH is
forwarded to 55222; release control/media are forwarded from guest 8765/8766 to host 18765/18766,
which the host Android emulator can reach as `10.0.2.2:18765` and `10.0.2.2:18766`.

Provisioning verifies a caller-supplied official ISO SHA-256 before creating any disk, generates a
random administrator password and Ed25519 key, restricts fixture ACLs, installs/configures the
guest SSH server, and records guest inventory. The stopped provisioned disk is the clean base.
Release runs use a separate qcow2 overlay and copied UEFI variables. Explicit `ResetRun
-ConfirmReset` removes only that working layer after validating every target is below the fixture
root.

Release actions transfer and independently hash the Windows ZIP, signed APK, and digest manifest;
invoke both packaged learner command files; make only the authenticated gateway ports reachable;
and require clean process/listener shutdown. ADR-0012 and `docs/testing/m8-clean-vm.md` define the
security and evidence boundary.

## Commands and results

```powershell
./scripts/m8-vm.ps1 -Action Prerequisites
```

Result: expected blocked exit code 2. QEMU, qemu-img, EDK2 firmware/variable template, WHPX,
OpenSSH client, memory, and disk checks passed. `iso_supplied` and `iso_exists` were false.

A first bounded QEMU argument probe correctly failed because the EDK2 code image was passed as a
legacy `-bios` file. The fixture was corrected to use separate EDK2 pflash code and persistent
variable drives. The second three-second probe successfully started QEMU with WHPX, q35, quoted
paths (including `Program Files` and a disk filename containing a space), pflash UEFI, and an IDE
qcow2 disk; that owned probe process was then stopped.

A second bounded process probe added QEMU's `-cpu max` model for the guest and also remained alive
under WHPX for three seconds before the owned process was stopped.

```powershell
$env:UV_CACHE_DIR = Join-Path (Resolve-Path '.cache').Path 'uv'
uv run --frozen pytest `
  apps/launcher/tests/test_distribution_entrypoints.py `
  tests/integration/test_m8_vm_fixture.py -q
```

Result: 6 passed. The tests cover normalized/forwarding Windows wrappers, fixed loopback/emulator
network topology, parseable unattended XML without a committed secret, required VM actions,
pflash use, and generated-key SSH provisioning.

```powershell
./scripts/package.ps1 -Version 0.1.3 -VersionCode 4 `
  -GradleUserHome 'C:\Users\PC\.gradle' -GradleOffline
```

The sandboxed attempt could not lock the existing external Gradle distribution. The approved
rerun passed Godot export, Android release build and RSA-3072 signature verification, embedded
CPython/hash-locked dependency installation, runtimes/source/notices, import smoke, direct doctor,
both packaged command-wrapper doctor smokes, and archive creation. The output is:

- Windows ZIP: 310,917,484 bytes; SHA-256
  `4d30b7eec83f4a1cf437178482b64b1dcb45c4a5689460d1e083b195dacf86bd`.
- Signed Android APK: 55,425,169 bytes; SHA-256
  `175265c7933fb3c41e6ab502a97b53bf693727be71590549dee0ab8ac5118bc0`; version name
  0.1.3, version code 4, and the existing release certificate.

The first full-suite attempt stopped on Ruff's static-XML warning in the new repository-template
test. After documenting that the input is trusted static source, the second attempt stopped on two
format-check differences. Formatting those tests and rerunning from the beginning passed: 162
Python tests at 85.51% branch coverage, 13 Kotlin tests, 8 C# tests, 17 real media tests, Godot
import/build/self-test, and the Android debug build.

The locked dependency audit initially hit the managed network denial; its approved retry reported
no known vulnerabilities. A new repository-local pre-commit cache likewise needed approved network
access to obtain its pinned hooks, after which every all-files hook passed. A later sandbox-only
rerun could not read that approved cache's hook manifest; repeating it in the same approved context
passed every hook again. `git diff --check` reported only the checkout's expected LF-to-CRLF
warnings. No QEMU/Godot/llama process or listener on ports 55222, 18765, 18766, or 8765-8768
remained active.

## Missing execution

No Windows guest was provisioned because the official evaluation ISO requires the user to complete
Microsoft's registration/download flow. Consequently no guest setup, model download, Godot
launch, VM-to-emulator pairing/media, or guest shutdown evidence exists. QEMU standard VGA's Godot
compatibility is specifically unverified. Milestone 8 remains blocked and no milestone commit is
allowed. Nothing here changes any Milestone 9 physical-hardware row.
