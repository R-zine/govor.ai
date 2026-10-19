[CmdletBinding()]
param(
    [ValidateSet(
        'Prerequisites', 'Provision', 'ResumeProvision', 'FinalizeProvision',
        'Start', 'Status', 'Stop', 'ResetRun',
        'StageRelease', 'SetupRelease', 'StartRelease', 'ReleaseStatus', 'WaitRelease'
    )]
    [string]$Action = 'Status',
    [string]$IsoPath = '',
    [string]$IsoSha256 = '',
    [string]$SetupProductKey = '',
    [ValidateRange(1, 32)]
    [int]$ImageIndex = 1,
    [string]$Version = '0.1.4',
    [ValidateRange(30, 300)]
    [int]$SmokeSeconds = 300,
    [switch]$ShowWindow,
    [switch]$ConfirmReset
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$configPath = Join-Path $script:RepositoryRoot 'config\m8-vm.json'
$config = Get-Content -LiteralPath $configPath -Raw -Encoding utf8 | ConvertFrom-Json
$vmRoot = Join-Path $script:CacheRoot 'm8-vm'
$seedRoot = Join-Path $vmRoot 'seed'
$baseDiskPath = Join-Path $vmRoot 'windows-base.qcow2'
$runDiskPath = Join-Path $vmRoot 'windows-run.qcow2'
$statePath = Join-Path $vmRoot 'state.json'
$metadataPath = Join-Path $vmRoot 'provisioning-source.json'
$runMetadataPath = Join-Path $vmRoot 'run-source.json'
$privateKey = Join-Path $vmRoot 'id_ed25519'
$publicKey = "$privateKey.pub"
$knownHosts = Join-Path $vmRoot 'known_hosts'
$passwordPath = Join-Path $vmRoot 'admin-password.dpapi'
$qemuLog = Join-Path $vmRoot 'qemu.stdout.log'
$qemuErrorLog = Join-Path $vmRoot 'qemu.stderr.log'
$releaseLog = Join-Path $vmRoot 'release.log'
$releaseEvidence = Join-Path $vmRoot 'release-evidence.json'
$qemu = 'C:\Program Files\qemu\qemu-system-x86_64.exe'
$qemuImg = 'C:\Program Files\qemu\qemu-img.exe'
$firmware = 'C:\Program Files\qemu\share\edk2-x86_64-code.fd'
$firmwareVariablesTemplate = 'C:\Program Files\qemu\share\edk2-i386-vars.fd'
$baseFirmwareVariables = Join-Path $vmRoot 'uefi-vars-base.fd'
$runFirmwareVariables = Join-Path $vmRoot 'uefi-vars-run.fd'
$ssh = (Get-Command 'ssh.exe' -ErrorAction SilentlyContinue).Source
$scp = (Get-Command 'scp.exe' -ErrorAction SilentlyContinue).Source

if ($Version -notmatch '^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$') {
    throw 'Version must be a semantic version suitable for a release artifact name.'
}
if ([int]$config.guest_control_port -ne 8765 -or [int]$config.guest_media_port -ne 8766) {
    throw 'The VM guest ports must match the fixed release launcher ports 8765 and 8766.'
}
if ([int]$config.ice_host_port -ne [int]$config.guest_ice_port) {
    throw 'The VM fixture requires a matching host/guest UDP ICE port.'
}
$hostPorts = @(
    [int]$config.monitor_host_port,
    [int]$config.ssh_host_port,
    [int]$config.control_host_port,
    [int]$config.media_host_port,
    [int]$config.ice_host_port
)
if (($hostPorts | Sort-Object -Unique).Count -ne $hostPorts.Count) {
    throw 'The VM host-forward ports must be unique.'
}

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding($false)))
}

function Update-ProvisioningBootstrap {
    if (-not (Test-Path -LiteralPath $publicKey -PathType Leaf)) {
        throw 'The VM SSH public key is missing.'
    }
    $publicKeyValue = (Get-Content -LiteralPath $publicKey -Raw).Trim()
    $bootstrapTemplate = Get-Content -LiteralPath (
        Join-Path $script:RepositoryRoot 'distribution\vm\bootstrap.ps1.template'
    ) -Raw
    Write-Utf8NoBom -Path (Join-Path $seedRoot 'bootstrap.ps1') `
        -Content $bootstrapTemplate.Replace('{{SSH_PUBLIC_KEY}}', $publicKeyValue)
}

function Convert-ToQemuPath {
    param([string]$Path)
    return ([IO.Path]::GetFullPath($Path)).Replace('\', '/')
}

function Protect-QemuPathArgument {
    param([string]$Path)
    $normalized = Convert-ToQemuPath $Path
    if ($normalized.Contains('"')) { throw "QEMU path contains an unsupported quote: $normalized" }
    return '"' + $normalized + '"'
}

function Get-RandomPassword {
    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) }
    finally { $generator.Dispose() }
    return ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+', 'A').Replace('/', 'B')
}

function Get-QemuVersion {
    if (-not (Test-Path -LiteralPath $qemu -PathType Leaf)) { return '' }
    $line = (& $qemu --version 2>$null | Select-Object -First 1)
    if ($line -match 'version\s+(\d+\.\d+\.\d+)') { return $Matches[1] }
    return ''
}

function Protect-VmRoot {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls.exe $vmRoot /inheritance:r /grant:r "${identity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Unable to protect the VM state directory: $vmRoot" }
}

function Save-State {
    param([Diagnostics.Process]$Process, [string]$Mode)
    $state = [ordered]@{
        schema_version = 1
        pid = $Process.Id
        mode = $Mode
        started_at = (Get-Date).ToUniversalTime().ToString('o')
    }
    Write-Utf8NoBom -Path $statePath -Content (($state | ConvertTo-Json -Depth 4) + "`n")
}

function Get-QemuProcess {
    if (-not (Test-Path -LiteralPath $statePath)) { return $null }
    try { $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json }
    catch { return $null }
    $process = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    try {
        if ([IO.Path]::GetFullPath($process.Path) -ne [IO.Path]::GetFullPath($qemu)) { return $null }
    }
    catch { return $null }
    return $process
}

function Assert-PortFree {
    param([int]$Port)
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listener) { throw "Host TCP port $Port is already in use." }
}

function Send-QemuCdBootKey {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $client.Connect('127.0.0.1', [int]$config.monitor_host_port)
        $stream = $client.GetStream()
        $payload = [Text.Encoding]::ASCII.GetBytes("sendkey a`n")
        $stream.Write($payload, 0, $payload.Length)
        $stream.Flush()
        Start-Sleep -Milliseconds 100
    }
    finally { $client.Dispose() }
}

function Get-SshArguments {
    return @(
        '-i', $privateKey,
        '-p', [string]$config.ssh_host_port,
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=5',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-o', "UserKnownHostsFile=$knownHosts"
    )
}

function Invoke-GuestPowerShell {
    param([Parameter(Mandatory = $true)][string]$Script, [switch]$AllowFailure)
    if (-not $ssh) { throw 'The Windows OpenSSH client is unavailable.' }
    $arguments = (Get-SshArguments) + @(
        "$($config.guest_user)@127.0.0.1",
        'powershell.exe -NoLogo -NoProfile -NonInteractive -Command ' +
        '"$source=[Console]::In.ReadToEnd(); ^& ([ScriptBlock]::Create($source))"'
    )
    $Script | & $ssh @arguments
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "Guest PowerShell failed with exit code $code."
    }
    return $code
}

function Test-GuestSsh {
    if (-not (Test-Path -LiteralPath $privateKey) -or -not $ssh) { return $false }
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell promotes native stderr to an ErrorRecord. A refused or incomplete SSH
        # handshake is the expected readiness result while Windows Setup is still running.
        $ErrorActionPreference = 'Continue'
        Invoke-GuestPowerShell -Script "Write-Output 'GOVOR_M8_SSH_READY'" `
            -AllowFailure 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch { return $false }
    finally { $ErrorActionPreference = $previousErrorActionPreference }
}

function Start-Qemu {
    param(
        [Parameter(Mandatory = $true)][string]$Disk,
        [Parameter(Mandatory = $true)][string]$FirmwareVariables,
        [switch]$Install,
        [switch]$AttachSeed,
        [string]$InstallationIso = ''
    )
    if (Get-QemuProcess) { throw 'The Milestone 8 VM is already running.' }
    foreach ($port in @($config.ssh_host_port, $config.control_host_port, $config.media_host_port)) {
        Assert-PortFree -Port ([int]$port)
    }
    $icePort = [int]$config.ice_host_port
    if (Get-NetUDPEndpoint -LocalPort $icePort -ErrorAction SilentlyContinue) {
        throw "UDP port $icePort is already in use."
    }
    $disk = Protect-QemuPathArgument $Disk
    $firmwareArgument = Protect-QemuPathArgument $firmware
    $firmwareVariablesArgument = Protect-QemuPathArgument $FirmwareVariables
    $arguments = @(
        '-name', [string]$config.machine_name,
        '-machine', 'q35,accel=whpx',
        # A fixed modern model supplies Windows 11's SSE4.2/POPCNT baseline while
        # avoiding the QEMU 11/WHPX pre-UEFI hang observed with host/max models.
        '-cpu', 'Skylake-Client-v4',
        '-smp', [string]$config.cpu_count,
        '-m', [string]$config.memory_mib,
        '-drive', "if=pflash,format=raw,readonly=on,file=$firmwareArgument",
        '-drive', "if=pflash,format=raw,file=$firmwareVariablesArgument",
        '-drive', "file=$disk,if=ide,format=qcow2,cache=writeback",
        '-device', 'e1000e,netdev=net0',
        '-netdev', "user,id=net0,hostname=GOVOR-M8-VM,hostfwd=tcp:127.0.0.1:$($config.ssh_host_port)-:$($config.guest_ssh_port),hostfwd=tcp:127.0.0.1:$($config.control_host_port)-:$($config.guest_control_port),hostfwd=tcp:127.0.0.1:$($config.media_host_port)-:$($config.guest_media_port),hostfwd=udp:127.0.0.1:$($config.ice_host_port)-:$($config.guest_ice_port)",
        '-monitor', "tcp:127.0.0.1:$($config.monitor_host_port),server=on,wait=off",
        '-rtc', 'base=localtime',
        '-vga', 'std'
    )
    if ($Install) {
        $iso = Protect-QemuPathArgument $InstallationIso
        $arguments += @('-drive', "file=$iso,media=cdrom,readonly=on")
    }
    if ($Install -or $AttachSeed) {
        $seed = Protect-QemuPathArgument $seedRoot
        $arguments += @(
            '-drive', "file=fat:$seed,format=raw,readonly=on,if=none,id=seed",
            '-device', 'qemu-xhci,id=xhci',
            '-device', 'usb-kbd,bus=xhci.0',
            '-device', 'usb-storage,drive=seed,removable=on'
        )
    }
    $arguments += $(if ($Install) { @('-boot', 'order=d,menu=on') } else { @('-boot', 'order=c') })
    if (-not $ShowWindow) { $arguments += @('-display', 'none') }

    foreach ($log in @($qemuLog, $qemuErrorLog)) {
        if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force }
    }
    $windowStyle = if ($ShowWindow) { 'Normal' } else { 'Hidden' }
    $process = Start-Process -FilePath $qemu -ArgumentList $arguments -PassThru `
        -WindowStyle $windowStyle -RedirectStandardOutput $qemuLog -RedirectStandardError $qemuErrorLog
    if ($Install) {
        # Cover EDK2's short Windows DVD input window without relying on a live WHPX reset.
        foreach ($attempt in 1..30) {
            Start-Sleep -Milliseconds 500
            if ($process.HasExited) { break }
            Send-QemuCdBootKey
        }
    }
    else { Start-Sleep -Seconds 3 }
    if ($process.HasExited) {
        $details = if (Test-Path -LiteralPath $qemuErrorLog) {
            Get-Content -LiteralPath $qemuErrorLog -Raw
        } else { 'no QEMU diagnostic was produced' }
        throw "QEMU exited during startup: $details"
    }
    Save-State -Process $process -Mode $(if ($Install -or $AttachSeed) { 'provisioning' } else { 'running' })
    Write-Output "VM process started: PID $($process.Id)"
}

function Assert-GuestReady {
    if (-not (Get-QemuProcess)) { throw 'The Milestone 8 VM is not running.' }
    if (-not (Test-GuestSsh)) { throw 'The Milestone 8 VM SSH endpoint is not ready.' }
}

function Copy-ToGuest {
    param([Parameter(Mandatory = $true)][string[]]$Paths, [Parameter(Mandatory = $true)][string]$Destination)
    if (-not $scp) { throw 'The Windows OpenSSH scp client is unavailable.' }
    $arguments = @(
        '-i', $privateKey,
        '-P', [string]$config.ssh_host_port,
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-o', "UserKnownHostsFile=$knownHosts"
    ) + $Paths + @("$($config.guest_user)@127.0.0.1:$Destination")
    & $scp @arguments
    if ($LASTEXITCODE -ne 0) { throw "scp failed with exit code $LASTEXITCODE." }
}

switch ($Action) {
    'Prerequisites' {
        $checks = [ordered]@{
            qemu = Test-Path -LiteralPath $qemu
            qemu_version = Get-QemuVersion
            qemu_version_matches = $false
            qemu_img = Test-Path -LiteralPath $qemuImg
            uefi_firmware = Test-Path -LiteralPath $firmware
            uefi_variables_template = Test-Path -LiteralPath $firmwareVariablesTemplate
            ssh_client = [bool]$ssh
            scp_client = [bool]$scp
            whpx_accelerator = $false
            host_memory_gib = 0
            host_free_disk_gib = [math]::Round(([IO.DriveInfo]::new('C')).AvailableFreeSpace / 1GB, 1)
            iso_supplied = [bool]$IsoPath
            iso_exists = $false
            reference_iso_page = [string]$config.reference_iso_page
        }
        if ($checks.qemu) {
            $accelerators = & $qemu -accel help 2>$null
            $checks.whpx_accelerator = [bool]($accelerators -match '^whpx$')
            $checks.qemu_version_matches = $checks.qemu_version -eq [string]$config.qemu_version
        }
        if (-not ('GovorVmMemory' -as [type])) {
            Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class GovorVmMemory { [StructLayout(LayoutKind.Sequential)] public class Status { public uint length=(uint)Marshal.SizeOf(typeof(Status)); public uint load; public ulong total; public ulong available; public ulong totalPage; public ulong availablePage; public ulong totalVirtual; public ulong availableVirtual; public ulong availableExtended; } [DllImport("kernel32.dll")] public static extern bool GlobalMemoryStatusEx([In,Out] Status status); }'
        }
        $memory = New-Object GovorVmMemory+Status
        [void][GovorVmMemory]::GlobalMemoryStatusEx($memory)
        $checks.host_memory_gib = [math]::Round($memory.total / 1GB, 1)
        if ($IsoPath) { $checks.iso_exists = Test-Path -LiteralPath $IsoPath -PathType Leaf }
        [pscustomobject]$checks | Format-List
        $failed = -not ($checks.qemu -and $checks.qemu_version_matches -and
            $checks.qemu_img -and $checks.uefi_firmware -and
            $checks.uefi_variables_template -and
            $checks.ssh_client -and $checks.scp_client -and $checks.whpx_accelerator -and
            $checks.host_memory_gib -ge 16 -and $checks.host_free_disk_gib -ge 120 -and
            $checks.iso_exists)
        if ($failed) { exit 2 }
        exit 0
    }
    'Provision' {
        foreach ($requiredPath in @($qemu, $qemuImg, $firmware, $firmwareVariablesTemplate)) {
            if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
                throw "VM prerequisite is missing: $requiredPath"
            }
        }
        $actualQemuVersion = Get-QemuVersion
        if ($actualQemuVersion -ne [string]$config.qemu_version) {
            throw "QEMU version mismatch: expected $($config.qemu_version), got $actualQemuVersion"
        }
        if (-not $ssh -or -not $scp) {
            throw 'The Windows OpenSSH client (ssh.exe and scp.exe) is required.'
        }
        $accelerators = & $qemu -accel help 2>$null
        if (-not ($accelerators -match '^whpx$')) {
            throw 'This QEMU build does not expose the WHPX accelerator.'
        }
        if (-not $IsoPath -or -not (Test-Path -LiteralPath $IsoPath -PathType Leaf)) {
            throw 'Provision requires -IsoPath pointing to a Windows 11 x64 installation ISO supplied for testing.'
        }
        if ($IsoSha256 -notmatch '^[0-9a-fA-F]{64}$') {
            throw 'Provision requires the recorded 64-character -IsoSha256 value.'
        }
        if ($SetupProductKey -and $SetupProductKey -notmatch '^[A-Za-z0-9]{5}(?:-[A-Za-z0-9]{5}){4}$') {
            throw 'SetupProductKey must be a five-by-five Windows setup key when supplied.'
        }
        foreach ($existingTarget in @(
            $baseDiskPath, $runDiskPath, $baseFirmwareVariables, $runFirmwareVariables
        )) {
            if (Test-Path -LiteralPath $existingTarget) {
                throw "VM state already exists. Refusing to overwrite it: $existingTarget"
            }
        }
        $actualIsoHash = (Get-FileHash -LiteralPath $IsoPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualIsoHash -ne $IsoSha256.ToLowerInvariant()) {
            throw "Windows ISO digest mismatch: expected $($IsoSha256.ToLowerInvariant()), got $actualIsoHash"
        }
        New-Item -ItemType Directory -Path $vmRoot, $seedRoot -Force | Out-Null
        Protect-VmRoot
        if (Test-Path -LiteralPath $knownHosts) { Remove-Item -LiteralPath $knownHosts -Force }
        $hasPrivateKey = Test-Path -LiteralPath $privateKey -PathType Leaf
        $hasPublicKey = Test-Path -LiteralPath $publicKey -PathType Leaf
        if ($hasPrivateKey -xor $hasPublicKey) {
            throw 'The VM SSH key pair is incomplete. Inspect the fixture state before retrying.'
        }
        if (-not $hasPrivateKey) {
            Invoke-Checked -FilePath 'ssh-keygen.exe' -ArgumentList @(
                # Windows PowerShell 5 drops a literal empty array element before invoking a native
                # executable. Preserve the quoted empty passphrase on the native command line.
                '-q', '-t', 'ed25519', '-f', $privateKey, '-N', '""', '-C', 'govor-m8-vm'
            )
        }
        $password = Get-RandomPassword
        $securePassword = ConvertTo-SecureString -String $password -AsPlainText -Force
        Write-Utf8NoBom -Path $passwordPath -Content ((ConvertFrom-SecureString $securePassword) + "`n")
        $unattendTemplate = Get-Content -LiteralPath (
            Join-Path $script:RepositoryRoot 'distribution\vm\Autounattend.xml.template'
        ) -Raw
        $productKeyBlock = if ($SetupProductKey) {
            '<ProductKey><Key>' + $SetupProductKey.ToUpperInvariant() + '</Key><WillShowUI>OnError</WillShowUI></ProductKey>'
        } else { '' }
        $unattend = $unattendTemplate.Replace('{{IMAGE_INDEX}}', [string]$ImageIndex).
            Replace('{{ADMIN_PASSWORD}}', $password).
            Replace('{{PRODUCT_KEY_BLOCK}}', $productKeyBlock)
        Write-Utf8NoBom -Path (Join-Path $seedRoot 'Autounattend.xml') -Content $unattend
        Update-ProvisioningBootstrap
        Write-Utf8NoBom -Path (Join-Path $seedRoot 'govor-m8-seed.marker') `
            -Content "govor.ai-m8-vm-seed-v1`n"
        $metadata = [ordered]@{
            schema_version = 1
            reference_iso_page = [string]$config.reference_iso_page
            iso_path = [IO.Path]::GetFullPath($IsoPath)
            iso_sha256 = $actualIsoHash
            image_index = $ImageIndex
            setup_product_key_provided = [bool]$SetupProductKey
            provision_started_at = (Get-Date).ToUniversalTime().ToString('o')
        }
        Write-Utf8NoBom -Path $metadataPath -Content (($metadata | ConvertTo-Json -Depth 4) + "`n")
        Copy-Item -LiteralPath $firmwareVariablesTemplate -Destination $baseFirmwareVariables
        Invoke-Checked -FilePath $qemuImg -ArgumentList @(
            'create', '-f', 'qcow2', $baseDiskPath, "$($config.disk_gib)G"
        )
        Start-Qemu -Disk $baseDiskPath -FirmwareVariables $baseFirmwareVariables `
            -Install -InstallationIso $IsoPath
        Write-Output 'Unattended provisioning started. Use -Action Status until provisioned.json reports ready.'
        exit 0
    }
    'ResumeProvision' {
        if (Get-QemuProcess) { throw 'The Milestone 8 VM is already running.' }
        foreach ($requiredPath in @($baseDiskPath, $baseFirmwareVariables, $metadataPath)) {
            if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
                throw "Provisioning state is missing: $requiredPath"
            }
        }
        $provisionedPath = Join-Path $seedRoot 'provisioned.json'
        if (Test-Path -LiteralPath $provisionedPath -PathType Leaf) {
            throw 'Provisioning already produced provisioned.json; use Start for an acceptance run.'
        }
        Update-ProvisioningBootstrap
        Start-Qemu -Disk $baseDiskPath -FirmwareVariables $baseFirmwareVariables -AttachSeed
        Write-Output 'Provisioning resume started from the existing base disk.'
        exit 0
    }
    'FinalizeProvision' {
        Assert-GuestReady
        $provisionedPath = Join-Path $seedRoot 'provisioned.json'
        if (Test-Path -LiteralPath $provisionedPath -PathType Leaf) {
            throw 'Provisioning was already finalized.'
        }
        $output = @(Invoke-GuestPowerShell -Script @'
$path = 'C:\GovorM8\provisioning.json'
if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { exit 42 }
$bytes = [Text.Encoding]::UTF8.GetBytes((Get-Content -LiteralPath $path -Raw))
Write-Output ('GOVOR_PROVISIONING:' + [Convert]::ToBase64String($bytes))
'@)
        $record = $output | Where-Object { $_ -is [string] -and $_.StartsWith('GOVOR_PROVISIONING:') } |
            Select-Object -Last 1
        if (-not $record) { throw 'The guest did not return its provisioning record.' }
        $json = [Text.Encoding]::UTF8.GetString(
            [Convert]::FromBase64String($record.Substring('GOVOR_PROVISIONING:'.Length))
        )
        $provisioning = $json | ConvertFrom-Json
        if ($provisioning.status -ne 'ready') {
            throw "Guest provisioning status is $($provisioning.status): $($provisioning.message)"
        }
        Write-Utf8NoBom -Path $provisionedPath -Content ($json.TrimEnd() + "`n")
        Invoke-GuestPowerShell -Script "shutdown.exe /s /t 0 /c 'govor.ai M8 provisioning finalized'" `
            -AllowFailure | Out-Null
        $deadline = (Get-Date).AddSeconds(60)
        while ((Get-QemuProcess) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 1 }
        if (Get-QemuProcess) { throw 'The finalized provisioning guest did not stop within 60 seconds.' }
        Write-Output 'Provisioning record retrieved and clean base stopped.'
        exit 0
    }
    'Start' {
        if (-not (Test-Path -LiteralPath $baseDiskPath)) {
            throw 'Provision the VM before starting it.'
        }
        $provisionedPath = Join-Path $seedRoot 'provisioned.json'
        if (-not (Test-Path -LiteralPath $provisionedPath)) {
            throw 'Provisioning has not produced seed\provisioned.json.'
        }
        $provisioned = Get-Content -LiteralPath $provisionedPath -Raw | ConvertFrom-Json
        if ($provisioned.status -ne 'ready') { throw "Provisioning status is $($provisioned.status)." }
        if (-not (Test-Path -LiteralPath $baseFirmwareVariables -PathType Leaf)) {
            throw 'The provisioned VM UEFI variable store is missing.'
        }
        $unattendPath = Join-Path $seedRoot 'Autounattend.xml'
        if (Test-Path -LiteralPath $unattendPath) { Remove-Item -LiteralPath $unattendPath -Force }
        if ((Test-Path -LiteralPath $runDiskPath) -xor
            (Test-Path -LiteralPath $runFirmwareVariables)) {
            throw 'The VM working layer is incomplete. Inspect it, then use ResetRun explicitly.'
        }
        if (-not (Test-Path -LiteralPath $runDiskPath)) {
            Invoke-Checked -FilePath $qemuImg -ArgumentList @(
                'create', '-f', 'qcow2', '-F', 'qcow2', '-b', $baseDiskPath, $runDiskPath
            )
            Copy-Item -LiteralPath $baseFirmwareVariables -Destination $runFirmwareVariables
            $runMetadata = [ordered]@{
                schema_version = 1
                clean_base_sha256 = (Get-FileHash -LiteralPath $baseDiskPath -Algorithm SHA256).Hash.ToLowerInvariant()
                created_at = (Get-Date).ToUniversalTime().ToString('o')
            }
            Write-Utf8NoBom -Path $runMetadataPath `
                -Content (($runMetadata | ConvertTo-Json -Depth 4) + "`n")
        }
        Start-Qemu -Disk $runDiskPath -FirmwareVariables $runFirmwareVariables
        Write-Output 'Wait for -Action Status to report ssh_ready: true.'
        exit 0
    }
    'Status' {
        $process = Get-QemuProcess
        $provisionedPath = Join-Path $seedRoot 'provisioned.json'
        $provisioning = if (Test-Path -LiteralPath $provisionedPath) {
            Get-Content -LiteralPath $provisionedPath -Raw | ConvertFrom-Json
        } else { $null }
        $sshReady = $false
        if ($process) { $sshReady = Test-GuestSsh }
        [pscustomobject]@{
            vm_root = $vmRoot
            clean_base_exists = Test-Path -LiteralPath $baseDiskPath
            run_overlay_exists = Test-Path -LiteralPath $runDiskPath
            running = [bool]$process
            pid = if ($process) { $process.Id } else { $null }
            provisioning_status = if ($provisioning) { $provisioning.status } else { 'not-created' }
            ssh_ready = $sshReady
            ssh_port = $config.ssh_host_port
            android_control_endpoint = "$($config.android_host_alias):$($config.control_host_port)"
            android_media_endpoint = "$($config.android_host_alias):$($config.media_host_port)"
        } | Format-List
        if ($provisioning) { $provisioning | ConvertTo-Json -Depth 6 }
        $provisionedReady = $provisioning -and $provisioning.status -eq 'ready'
        exit $(if ($sshReady) { 0 } elseif ($process) { 2 } elseif ($provisionedReady) { 0 } else { 1 })
    }
    'Stop' {
        $process = Get-QemuProcess
        if (-not $process) { Write-Output 'VM is already stopped.'; exit 0 }
        Assert-GuestReady
        Invoke-GuestPowerShell -Script "shutdown.exe /s /t 0 /c 'govor.ai M8 VM stop'" | Out-Null
        if (-not $process.WaitForExit(60000)) {
            throw 'The guest did not shut down within 60 seconds. The QEMU process was not forced.'
        }
        Write-Output 'VM shut down normally.'
        exit 0
    }
    'ResetRun' {
        if (-not $ConfirmReset) {
            throw 'ResetRun destroys the VM working layer. Repeat with -ConfirmReset.'
        }
        if (Get-QemuProcess) { throw 'Stop the VM normally before resetting its working layer.' }
        $vmRootFull = [IO.Path]::GetFullPath($vmRoot).TrimEnd('\') + '\'
        $targets = @(
            $runDiskPath, $runFirmwareVariables, $runMetadataPath,
            $releaseLog, $releaseEvidence
        )
        foreach ($target in $targets) {
            $resolvedTarget = [IO.Path]::GetFullPath($target)
            if (-not $resolvedTarget.StartsWith($vmRootFull, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Refusing to reset a path outside the VM fixture: $resolvedTarget"
            }
            if (Test-Path -LiteralPath $resolvedTarget) {
                Remove-Item -LiteralPath $resolvedTarget -Force
            }
        }
        Write-Output 'VM working layer removed. The next Start creates a clean run from the base.'
        exit 0
    }
    'StageRelease' {
        Assert-GuestReady
        $zip = Join-Path $script:CacheRoot "dist\govor.ai-$Version-windows-x64.zip"
        $apk = Join-Path $script:CacheRoot "dist\govor.ai-$Version-android-release.apk"
        $manifest = Join-Path $script:CacheRoot "dist\govor.ai-$Version-artifacts.json"
        foreach ($artifact in @($zip, $apk, $manifest)) {
            if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
                throw "Release artifact is missing: $artifact"
            }
        }
        $zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
        $apkHash = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
        $manifestHash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
        $manifestEntries = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
        $zipEntries = @($manifestEntries | Where-Object {
            $_.name -eq [IO.Path]::GetFileName($zip)
        })
        $apkEntries = @($manifestEntries | Where-Object {
            $_.name -eq [IO.Path]::GetFileName($apk)
        })
        if ($zipEntries.Count -ne 1 -or [string]$zipEntries[0].sha256 -ne $zipHash -or
            [int64]$zipEntries[0].size -ne (Get-Item -LiteralPath $zip).Length) {
            throw 'The host artifact manifest does not match the Windows ZIP.'
        }
        if ($apkEntries.Count -ne 1 -or [string]$apkEntries[0].sha256 -ne $apkHash -or
            [int64]$apkEntries[0].size -ne (Get-Item -LiteralPath $apk).Length) {
            throw 'The host artifact manifest does not match the Android APK.'
        }
        Invoke-GuestPowerShell -Script @'
$root = 'C:\GovorM8\candidate'
New-Item -ItemType Directory -Path $root -Force | Out-Null
'@ | Out-Null
        Copy-ToGuest -Paths @($zip, $apk, $manifest) -Destination 'C:/GovorM8/candidate/'
        $remote = @'
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$version = '{{VERSION}}'
$candidate = 'C:\GovorM8\candidate'
$zip = Join-Path $candidate "govor.ai-$version-windows-x64.zip"
$apk = Join-Path $candidate "govor.ai-$version-android-release.apk"
$manifest = Join-Path $candidate "govor.ai-$version-artifacts.json"
if ((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant() -ne '{{MANIFEST_HASH}}') {
    throw 'Guest artifact manifest hash mismatch.'
}
if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne '{{ZIP_HASH}}') {
    throw 'Guest Windows ZIP hash mismatch.'
}
if ((Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant() -ne '{{APK_HASH}}') {
    throw 'Guest Android APK hash mismatch.'
}
$manifestEntries = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
$zipEntries = @($manifestEntries | Where-Object { $_.name -eq [IO.Path]::GetFileName($zip) })
$apkEntries = @($manifestEntries | Where-Object { $_.name -eq [IO.Path]::GetFileName($apk) })
if ($zipEntries.Count -ne 1 -or [string]$zipEntries[0].sha256 -ne '{{ZIP_HASH}}' -or
    [int64]$zipEntries[0].size -ne (Get-Item -LiteralPath $zip).Length) {
    throw 'Guest artifact manifest does not describe the Windows ZIP.'
}
if ($apkEntries.Count -ne 1 -or [string]$apkEntries[0].sha256 -ne '{{APK_HASH}}' -or
    [int64]$apkEntries[0].size -ne (Get-Item -LiteralPath $apk).Length) {
    throw 'Guest artifact manifest does not describe the Android APK.'
}
$releases = 'C:\GovorM8\releases'
$target = Join-Path $releases $version
if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
New-Item -ItemType Directory -Path $target -Force | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath $target
$root = Join-Path $target "govor.ai-$version-windows-x64"
if (-not (Test-Path -LiteralPath (Join-Path $root 'Setup-Govor.cmd'))) {
    throw 'The extracted setup entrypoint is missing.'
}
$state = [ordered]@{
    version = $version
    install_root = $root
    zip_sha256 = '{{ZIP_HASH}}'
    apk_sha256 = '{{APK_HASH}}'
    staged_at = (Get-Date).ToUniversalTime().ToString('o')
}
[IO.File]::WriteAllText(
    'C:\GovorM8\release-state.json',
    (($state | ConvertTo-Json -Depth 4) + "`n"),
    (New-Object Text.UTF8Encoding($false))
)
$state | ConvertTo-Json -Depth 4
'@
        $remote = $remote.Replace('{{VERSION}}', $Version).
            Replace('{{ZIP_HASH}}', $zipHash).Replace('{{APK_HASH}}', $apkHash).
            Replace('{{MANIFEST_HASH}}', $manifestHash)
        Invoke-GuestPowerShell -Script $remote
        Write-Output 'Release staged and independently hashed inside the VM.'
        exit 0
    }
    'SetupRelease' {
        Assert-GuestReady
        $remote = @'
$ErrorActionPreference = 'Stop'
$state = Get-Content -LiteralPath 'C:\GovorM8\release-state.json' -Raw | ConvertFrom-Json
$setup = Join-Path $state.install_root 'Setup-Govor.cmd'
$command = "echo.|call `"$setup`""
& cmd.exe /d /s /c $command
if ($LASTEXITCODE -ne 0) { throw "Setup-Govor.cmd failed with exit code $LASTEXITCODE." }
$python = Join-Path $state.install_root 'runtime\python\python.exe'
$launcher = Join-Path $state.install_root 'app\apps\launcher\src'
$security = Join-Path $state.install_root 'app\packages\gateway_security\src'
$env:PYTHONPATH = "$launcher;$security"
& $python -m govor_launcher.cli --install-root $state.install_root model-status
if ($LASTEXITCODE -ne 0) { throw 'One or more release models are not ready.' }
'@
        Invoke-GuestPowerShell -Script $remote
        Write-Output 'Clean-VM setup wrapper and model verification passed.'
        exit 0
    }
    'StartRelease' {
        Assert-GuestReady
        $remote = @'
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$state = Get-Content -LiteralPath 'C:\GovorM8\release-state.json' -Raw | ConvertFrom-Json
$root = $state.install_root
$python = Join-Path $root 'runtime\python\python.exe'
$start = Join-Path $root 'Start-Govor.cmd'
$runner = @(
    '@echo off',
    'set "GOVOR_MEDIA_ICE_FIXTURE_ADVERTISE_HOST={{ICE_ADVERTISE_HOST}}"',
    'set "GOVOR_MEDIA_ICE_FIXTURE_BIND_PORT={{ICE_BIND_PORT}}"',
    'set "GOVOR_RENDERER_FIXTURE_TONE_DELAY_SECONDS=90"',
    "echo.|call `"$start`" --smoke-seconds {{SMOKE_SECONDS}} > C:\GovorM8\release.log 2>&1"
) -join "`r`n"
[IO.File]::WriteAllText('C:\GovorM8\run-release.cmd', $runner + "`r`n", [Text.Encoding]::ASCII)
Get-NetFirewallRule -Name 'Govor-M8-Control','Govor-M8-Media','Govor-M8-Ice' -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule
New-NetFirewallRule -Name 'Govor-M8-Control' -DisplayName 'govor.ai M8 control' -Direction Inbound `
    -Action Allow -Protocol TCP -LocalPort 8765 -Program $python -Profile Private | Out-Null
New-NetFirewallRule -Name 'Govor-M8-Media' -DisplayName 'govor.ai M8 media' -Direction Inbound `
    -Action Allow -Protocol TCP -LocalPort 8766 -Program $python -Profile Private | Out-Null
New-NetFirewallRule -Name 'Govor-M8-Ice' -DisplayName 'govor.ai M8 WebRTC ICE' -Direction Inbound `
    -Action Allow -Protocol UDP -LocalPort '{{ICE_BIND_PORT}}' -Program $python -Profile Private | Out-Null
Unregister-ScheduledTask -TaskName 'GovorM8Release' -Confirm:$false -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/d /c C:\GovorM8\run-release.cmd'
$principal = New-ScheduledTaskPrincipal -UserId "$env:COMPUTERNAME\GovorM8" `
    -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName 'GovorM8Release' -Action $action -Principal $principal | Out-Null
Start-ScheduledTask -TaskName 'GovorM8Release'
$deadline = (Get-Date).AddSeconds(240)
do {
    Start-Sleep -Seconds 2
    $ports = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object LocalPort -In 8765,8766)
    $task = Get-ScheduledTask -TaskName 'GovorM8Release'
    if ($task.State -ne 'Running') {
        $log = if (Test-Path 'C:\GovorM8\release.log') {
            Get-Content 'C:\GovorM8\release.log' -Tail 40 | Out-String
        } else { 'release log is missing' }
        throw "Release task exited before readiness: $log"
    }
} while ($ports.Count -lt 2 -and (Get-Date) -lt $deadline)
if ($ports.Count -lt 2) {
    $log = if (Test-Path 'C:\GovorM8\release.log') {
        Get-Content 'C:\GovorM8\release.log' -Tail 40 | Out-String
    } else { 'release log is missing' }
    throw "Release listeners did not become ready within 240 seconds: $log"
}
$detailsDeadline = (Get-Date).AddSeconds(30)
do {
    $detailsReady = (Test-Path 'C:\GovorM8\release.log' -PathType Leaf) -and
        (Select-String -LiteralPath 'C:\GovorM8\release.log' -SimpleMatch `
            'Certificate SHA-256:' -Quiet) -and
        (Select-String -LiteralPath 'C:\GovorM8\release.log' -SimpleMatch `
            'One-time pairing code:' -Quiet)
    if (-not $detailsReady) { Start-Sleep -Milliseconds 250 }
} while (-not $detailsReady -and (Get-Date) -lt $detailsDeadline)
if (-not $detailsReady) {
    throw 'Release listeners became ready, but pairing details were not flushed to the startup log.'
}
Write-Output 'GOVOR_M8_RELEASE_READY'
'@
        $remote = $remote.Replace('{{SMOKE_SECONDS}}', [string]$SmokeSeconds).
            Replace('{{ICE_ADVERTISE_HOST}}', [string]$config.android_host_alias).
            Replace('{{ICE_BIND_PORT}}', [string]$config.guest_ice_port)
        Invoke-GuestPowerShell -Script $remote
        $arguments = @(
            '-i', $privateKey, '-P', [string]$config.ssh_host_port,
            '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
            '-o', "UserKnownHostsFile=$knownHosts",
            "$($config.guest_user)@127.0.0.1:C:/GovorM8/release.log", $releaseLog
        )
        & $scp @arguments
        if ($LASTEXITCODE -ne 0) { throw 'Unable to retrieve the release startup log.' }
        Write-Output "Release is ready for up to $SmokeSeconds seconds. Pairing details: $releaseLog"
        Write-Output "Android control endpoint: $($config.android_host_alias):$($config.control_host_port)"
        Write-Output "Android media endpoint: $($config.android_host_alias):$($config.media_host_port)"
        exit 0
    }
    'ReleaseStatus' {
        Assert-GuestReady
        $remote = @'
$task = Get-ScheduledTask -TaskName 'GovorM8Release' -ErrorAction SilentlyContinue
$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object LocalPort -In 8765,8766,8767,8768)
$owned = @(Get-Process -ErrorAction SilentlyContinue |
    Where-Object ProcessName -In 'python','llama-server','GovorRenderer')
[pscustomobject]@{
    task_state = if ($task) { [string]$task.State } else { 'missing' }
    listener_count = $listeners.Count
    owned_process_count = $owned.Count
    log_exists = Test-Path 'C:\GovorM8\release.log'
} | ConvertTo-Json
'@
        Invoke-GuestPowerShell -Script $remote
        exit 0
    }
    'WaitRelease' {
        Assert-GuestReady
        $remote = @'
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$deadline = (Get-Date).AddSeconds({{WAIT_SECONDS}})
do {
    $task = Get-ScheduledTask -TaskName 'GovorM8Release' -ErrorAction SilentlyContinue
    if (-not $task -or $task.State -ne 'Running') { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($task -and $task.State -eq 'Running') { throw 'Release task did not finish before the deadline.' }
Start-Sleep -Seconds 3
$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object LocalPort -In 8765,8766,8767,8768)
$owned = @(Get-Process -ErrorAction SilentlyContinue |
    Where-Object ProcessName -In 'python','llama-server','GovorRenderer')
$result = [ordered]@{
    stopped_at = (Get-Date).ToUniversalTime().ToString('o')
    task_state = if ($task) { [string]$task.State } else { 'missing' }
    listener_count = $listeners.Count
    owned_process_count = $owned.Count
    clean_shutdown = ($listeners.Count -eq 0 -and $owned.Count -eq 0)
}
[IO.File]::WriteAllText(
    'C:\GovorM8\release-evidence.json',
    (($result | ConvertTo-Json -Depth 4) + "`n"),
    (New-Object Text.UTF8Encoding($false))
)
$result | ConvertTo-Json -Depth 4
if (-not $result.clean_shutdown) { exit 3 }
'@
        $remote = $remote.Replace('{{WAIT_SECONDS}}', [string]($SmokeSeconds + 120))
        Invoke-GuestPowerShell -Script $remote
        $arguments = @(
            '-i', $privateKey, '-P', [string]$config.ssh_host_port,
            '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new',
            '-o', "UserKnownHostsFile=$knownHosts",
            "$($config.guest_user)@127.0.0.1:C:/GovorM8/release-evidence.json", $releaseEvidence
        )
        & $scp @arguments
        if ($LASTEXITCODE -ne 0) { throw 'Unable to retrieve release shutdown evidence.' }
        Write-Output "Release stopped cleanly. Evidence: $releaseEvidence"
        exit 0
    }
}
