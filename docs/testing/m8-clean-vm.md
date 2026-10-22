# Milestone 8 local clean-Windows fixture

This runbook closes only the clean-Windows software row of Milestone 8. It uses a QEMU/WHPX
Windows guest for the PC release and the existing Android Studio emulator on the host. It never
counts as physical-phone, intended-Wi-Fi, acoustic, hardware-codec, target-performance,
monitor-off, thermal, or bounded-stability evidence; those later passed independently in
Milestone 9.

## One-time input

A Windows 11 Enterprise evaluation ISO from Microsoft's Evaluation Center is the recommended
reference input:

<https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise>

The user supplies the test ISO. Record its SHA-256 independently and verify the file before
provisioning. The fixture does not certify provenance, activation, or licensing; do not automate
activation bypass or commit/copy any ISO into a release artifact. QEMU, VM disks, generated
credentials, and logs remain under ignored `.cache/m8-vm`.

The accepted 2026-10-19 run used the exact user-supplied image documented in
`docs/benchmarks/2026-10-19-m8-clean-vm-acceptance.md`. It is not distributed with govor.ai, and
the passing result applies only to that recorded image and guest state.

## Provision the clean base

From the repository root, substitute the actual ISO path and its recorded digest:

```powershell
./scripts/m8-vm.ps1 -Action Prerequisites -IsoPath 'C:\path\Windows11Enterprise.iso'
./scripts/m8-vm.ps1 -Action Provision `
  -IsoPath 'C:\path\Windows11Enterprise.iso' `
  -IsoSha256 '<64-character-recorded-sha256>' `
  -ImageIndex 1 -ShowWindow
```

Provisioning is unattended but the visible window is useful for the first run. It creates a
random-password local administrator, installs OpenSSH Server, writes inventory evidence, and
shuts the guest down. Poll without changing the VM:

```powershell
./scripts/m8-vm.ps1 -Action Status
```

Continue only after `provisioning_status: ready` and `running: false`. A failed status is evidence
to diagnose, not permission to call the VM clean. The base disk and UEFI variables are retained
but never booted for release work.

## Create and prepare a clean acceptance run

Build a candidate whose version/code are newer than the last signed APK, then start the fixture:

```powershell
./scripts/package.ps1 -Version 0.1.4 -VersionCode 5
./scripts/m8-vm.ps1 -Action Start
./scripts/m8-vm.ps1 -Action Status
./scripts/m8-vm.ps1 -Action StageRelease -Version 0.1.4
./scripts/m8-vm.ps1 -Action SetupRelease
```

The first `Start` creates a mutable qcow2 overlay over the clean base. `StageRelease` verifies the
host artifacts, transfers them, independently verifies their hashes inside the guest, and extracts
the Windows package. Both sides require the manifest's sizes and hashes to match the ZIP/APK, and
the guest also verifies the transferred manifest hash. `SetupRelease` invokes the exact packaged
`Setup-Govor.cmd`; allow its first
model download to complete. No development Python, Godot editor, source checkout, Gradle, or
Android Studio is installed in the guest.

## Launch through the learner entry point and connect the host emulator

Start the bounded release run:

```powershell
./scripts/m8-vm.ps1 -Action StartRelease -Version 0.1.4 -SmokeSeconds 300
```

The action invokes the packaged `Start-Govor.cmd`, not the Python module directly. It retrieves
`.cache/m8-vm/release.log`, which contains the one-time pairing code and certificate SHA-256. In
the signed Android release UI enter:

- media: `10.0.2.2:18766`
- control: `10.0.2.2:18765`
- the current one-time pairing code
- the exact certificate fingerprint

Use the host Android SDK only to install/inspect the signed candidate and automate the emulator;
it is not installed in the clean guest. Before connecting, confirm no reverse mapping exists:

```powershell
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
& $adb devices -l
& $adb -s emulator-5554 reverse --list
& $adb -s emulator-5554 install -r '.cache\dist\govor.ai-0.1.4-android-release.apk'
```

Record pairing, WSS control/media connection, renderer startup, non-black/changing video evidence,
application audio, microphone-frame return, and any graphics/audio/firewall error exactly. The
fixture advertises one explicit UDP ICE candidate through host loopback port 18770 because the
guest's ordinary host candidate is unreachable through QEMU user networking. The override is
fixture-only and media remains DTLS-SRTP. These
emulator observations can corroborate launch but do not create new hardware evidence. If QEMU's
virtual display cannot run Godot in a repeat, record that attempt as failing; do not replace the
dated passing evidence or report the repeat as a pass.

The VM harness requests one locally muted, 90-second-delayed two-second application tone so ICE
can connect before PCM is published. Normal release startup remains silent. Do not turn this into
an unbounded or locally audible fixture.

## Prove bounded shutdown and stop the fixture

Use the same smoke duration passed to `StartRelease`:

```powershell
./scripts/m8-vm.ps1 -Action WaitRelease -SmokeSeconds 300
./scripts/m8-vm.ps1 -Action ReleaseStatus
./scripts/m8-vm.ps1 -Action Stop
```

`WaitRelease` fails unless guest listeners 8765-8768 and package-owned Python, llama-server, and
GovorRenderer processes are all gone. Preserve `.cache/m8-vm/release.log` and
`.cache/m8-vm/release-evidence.json`, and record the exact commands/results in `STATUS.md`,
`hardware-tests.md`, and a dated benchmark file.

## Repeat from the clean base

Reset only after a normal guest stop. This intentionally deletes the mutable acceptance layer and
all application/model/progress state inside it, while preserving the clean provisioned base:

```powershell
./scripts/m8-vm.ps1 -Action ResetRun -ConfirmReset
./scripts/m8-vm.ps1 -Action Start
```

Never delete or replace the base and call a run verified. Re-provision from the same
digest-verified input, or document and verify a new exact image, if the base changes or becomes
suspect.
