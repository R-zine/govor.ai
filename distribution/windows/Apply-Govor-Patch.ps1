[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InstallRoot,
    [string] $PatchPath = '',
    [switch] $NoPrompt,
    [switch] $DoctorOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$maximumFileCount = 20000
$maximumFileBytes = [long]8 * 1024 * 1024 * 1024
$maximumTotalBytes = [long]16 * 1024 * 1024 * 1024
$protectedPaths = @(
    'apply-govor-patch.cmd',
    'apply-govor-patch.ps1',
    'config/update-signing-public.xml'
)

function Assert-ExactProperties {
    param(
        [Parameter(Mandatory = $true)] [object] $Value,
        [Parameter(Mandatory = $true)] [string[]] $Expected,
        [Parameter(Mandatory = $true)] [string] $Label
    )
    $actual = @($Value.PSObject.Properties.Name | Sort-Object)
    $wanted = @($Expected | Sort-Object)
    if (($actual -join "`n") -cne ($wanted -join "`n")) {
        throw "$Label has unexpected or missing fields."
    }
}

function Assert-SemanticVersion {
    param([Parameter(Mandatory = $true)] [object] $Value, [Parameter(Mandatory = $true)] [string] $Label)
    if ($Value -isnot [string] -or $Value.Length -gt 80 -or
        $Value -cnotmatch '^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$') {
        throw "$Label must be a bounded semantic version."
    }
}

function Assert-Sha256 {
    param([Parameter(Mandatory = $true)] [object] $Value, [Parameter(Mandatory = $true)] [string] $Label)
    if ($Value -isnot [string] -or $Value -cnotmatch '^[0-9a-f]{64}$') {
        throw "$Label must be 64 lowercase hexadecimal characters."
    }
}

function Assert-IntegerRange {
    param(
        [Parameter(Mandatory = $true)] [object] $Value,
        [Parameter(Mandatory = $true)] [long] $Minimum,
        [Parameter(Mandatory = $true)] [long] $Maximum,
        [Parameter(Mandatory = $true)] [string] $Label
    )
    if ($Value -isnot [int] -and $Value -isnot [long]) {
        throw "$Label must be an integer."
    }
    if ([long]$Value -lt $Minimum -or [long]$Value -gt $Maximum) {
        throw "$Label is outside the accepted range."
    }
}

function Resolve-InstallPath {
    param([Parameter(Mandatory = $true)] [string] $RelativePath)
    if ($RelativePath.Length -gt 240 -or
        $RelativePath -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._/-]{0,239}$' -or
        $RelativePath.Contains('\') -or $RelativePath.Contains(':') -or
        $RelativePath.StartsWith('/') -or
        @($RelativePath.Split('/') | Where-Object { $_ -eq '' -or $_ -eq '.' -or $_ -eq '..' }).Count -ne 0) {
        throw "Unsafe application patch path: $RelativePath"
    }
    $candidate = [IO.Path]::GetFullPath((Join-Path $script:resolvedInstallRoot ($RelativePath.Replace('/', '\'))))
    if (-not $candidate.StartsWith($script:installPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Application patch path leaves the install directory: $RelativePath"
    }
    return $candidate
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)] [string] $Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-CurrentFile {
    param([Parameter(Mandatory = $true)] [object] $Operation)
    $target = Resolve-InstallPath -RelativePath ([string]$Operation.path)
    if ($Operation.action -eq 'add') {
        if (Test-Path -LiteralPath $target) {
            throw "Patch would overwrite an untracked local file: $($Operation.path)"
        }
        return
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) {
        throw "Required base file is missing: $($Operation.path)"
    }
    if ((Get-Item -LiteralPath $target).Length -ne [long]$Operation.old_size -or
        (Get-Sha256 -Path $target) -cne [string]$Operation.old_sha256) {
        throw "Required base file was locally changed or is from another release: $($Operation.path)"
    }
}

function Test-LocalPort {
    param([Parameter(Mandatory = $true)] [int] $Port)
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $attempt = $client.ConnectAsync('127.0.0.1', $Port)
        if (-not $attempt.Wait(200)) { return $false }
        return $client.Connected
    }
    catch { return $false }
    finally { $client.Dispose() }
}

function Copy-ArchiveEntryChecked {
    param(
        [Parameter(Mandatory = $true)] [IO.Compression.ZipArchiveEntry] $Entry,
        [Parameter(Mandatory = $true)] [string] $Destination,
        [Parameter(Mandatory = $true)] [long] $ExpectedSize,
        [Parameter(Mandatory = $true)] [string] $ExpectedSha256
    )
    if ($Entry.Length -ne $ExpectedSize) {
        throw "Patch payload has the wrong size: $($Entry.FullName)"
    }
    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $input = $Entry.Open()
    $output = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $input.CopyTo($output) }
    finally {
        $output.Dispose()
        $input.Dispose()
    }
    if ((Get-Item -LiteralPath $Destination).Length -ne $ExpectedSize -or
        (Get-Sha256 -Path $Destination) -cne $ExpectedSha256) {
        throw "Patch payload failed SHA-256 verification: $($Entry.FullName)"
    }
}

$resolvedInstallRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath $resolvedInstallRoot -PathType Container)) {
    throw "The govor.ai install directory does not exist: $resolvedInstallRoot"
}
$installPrefix = $resolvedInstallRoot + [IO.Path]::DirectorySeparatorChar

if ($DoctorOnly) {
    $doctorReleasePath = Join-Path $resolvedInstallRoot 'config\release.json'
    $doctorPublicKeyPath = Join-Path $resolvedInstallRoot 'config\update-signing-public.xml'
    if (-not (Test-Path -LiteralPath $doctorReleasePath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $doctorPublicKeyPath -PathType Leaf)) {
        throw 'Application patch release metadata or public key is missing.'
    }
    $doctorRelease = Get-Content -LiteralPath $doctorReleasePath -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-ExactProperties -Value $doctorRelease -Expected @(
        'format_version', 'version', 'android'
    ) -Label 'Release metadata'
    if ($doctorRelease.format_version -ne 1) { throw 'Unsupported release metadata format.' }
    Assert-SemanticVersion -Value $doctorRelease.version -Label 'Installed release version'
    $doctorRsa = [Security.Cryptography.RSACryptoServiceProvider]::new(3072)
    $doctorRsa.PersistKeyInCsp = $false
    try {
        $doctorRsa.FromXmlString((Get-Content -LiteralPath $doctorPublicKeyPath -Raw -Encoding utf8))
        if ($doctorRsa.KeySize -lt 3072) { throw 'Application update key must be at least RSA-3072.' }
    }
    finally { $doctorRsa.Dispose() }
    Write-Output 'Application patch prerequisites: ready'
    exit 0
}

if (-not $PatchPath) {
    if ($NoPrompt) { throw 'PatchPath is required when NoPrompt is used.' }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [Windows.Forms.OpenFileDialog]::new()
    $dialog.Title = 'Choose a signed govor.ai application patch'
    $dialog.Filter = 'govor.ai application patch (*.govorpatch;*.zip)|*.govorpatch;*.zip'
    $dialog.Multiselect = $false
    if ($dialog.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) {
        Write-Output 'No application patch was selected.'
        exit 0
    }
    $PatchPath = $dialog.FileName
}
$resolvedPatch = [IO.Path]::GetFullPath($PatchPath)
if (-not (Test-Path -LiteralPath $resolvedPatch -PathType Leaf)) {
    throw "Application patch was not found: $resolvedPatch"
}
foreach ($port in @(8765, 8766, 8767)) {
    if (Test-LocalPort -Port $port) {
        throw "govor.ai appears to be running on TCP port $port. Stop it before applying a patch."
    }
}

$releasePath = Join-Path $resolvedInstallRoot 'config\release.json'
$publicKeyPath = Join-Path $resolvedInstallRoot 'config\update-signing-public.xml'
if (-not (Test-Path -LiteralPath $releasePath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $publicKeyPath -PathType Leaf)) {
    throw 'This release predates signed application patches. Install one updater-capable full release first.'
}
$release = Get-Content -LiteralPath $releasePath -Raw -Encoding utf8 | ConvertFrom-Json
Assert-ExactProperties -Value $release -Expected @('format_version', 'version', 'android') -Label 'Release metadata'
if ($release.format_version -ne 1) { throw 'Unsupported release metadata format.' }
Assert-SemanticVersion -Value $release.version -Label 'Installed release version'
Assert-ExactProperties -Value $release.android -Expected @(
    'application_id', 'version_code', 'version_name', 'signer_sha256'
) -Label 'Installed Android metadata'
if ($release.android.application_id -cne 'ai.govor.app' -or
    $release.android.version_name -cne $release.version) {
    throw 'Installed Android release identity is invalid.'
}
Assert-IntegerRange -Value $release.android.version_code -Minimum 1 -Maximum 2100000000 -Label 'Installed Android version code'
Assert-Sha256 -Value $release.android.signer_sha256 -Label 'Installed Android signer SHA-256'

$dataRoot = if ($env:GOVOR_DATA_ROOT) {
    [IO.Path]::GetFullPath($env:GOVOR_DATA_ROOT)
}
else {
    Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'govor.ai'
}
$updatesRoot = Join-Path $dataRoot 'updates'
New-Item -ItemType Directory -Force -Path $updatesRoot | Out-Null

$archiveStream = [IO.File]::Open($resolvedPatch, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
$archive = [IO.Compression.ZipArchive]::new($archiveStream, [IO.Compression.ZipArchiveMode]::Read, $false)
$stageRoot = $null
$androidDestination = $null
$committed = [Collections.Generic.List[object]]::new()
try {
    if ($archive.Entries.Count -gt ($maximumFileCount + 3)) {
        throw 'Application patch contains too many archive entries.'
    }
    $entries = [Collections.Generic.Dictionary[string, IO.Compression.ZipArchiveEntry]]::new(
        [StringComparer]::OrdinalIgnoreCase
    )
    foreach ($entry in $archive.Entries) {
        if ($entries.ContainsKey($entry.FullName)) {
            throw "Application patch contains a duplicate or case-colliding entry: $($entry.FullName)"
        }
        $entries.Add($entry.FullName, $entry)
    }
    if (-not $entries.ContainsKey('manifest.json') -or -not $entries.ContainsKey('manifest.sig')) {
        throw 'Application patch is missing its signed manifest.'
    }
    if ($entries['manifest.json'].Length -gt 16MB -or $entries['manifest.sig'].Length -gt 16KB) {
        throw 'Application patch manifest or signature exceeds its size limit.'
    }
    $manifestStream = [IO.MemoryStream]::new()
    $manifestInput = $entries['manifest.json'].Open()
    try { $manifestInput.CopyTo($manifestStream) }
    finally { $manifestInput.Dispose() }
    $manifestBytes = $manifestStream.ToArray()
    $manifestStream.Dispose()
    $signatureReader = [IO.StreamReader]::new($entries['manifest.sig'].Open(), [Text.Encoding]::ASCII)
    try { $signature = [Convert]::FromBase64String($signatureReader.ReadToEnd().Trim()) }
    finally { $signatureReader.Dispose() }

    $rsa = [Security.Cryptography.RSACryptoServiceProvider]::new(3072)
    $rsa.PersistKeyInCsp = $false
    try {
        $rsa.FromXmlString((Get-Content -LiteralPath $publicKeyPath -Raw -Encoding utf8))
        if ($rsa.KeySize -lt 3072 -or -not $rsa.VerifyData($manifestBytes, 'SHA256', $signature)) {
            throw 'Application patch signature is invalid.'
        }
    }
    finally { $rsa.Dispose() }

    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    $manifest = $utf8.GetString($manifestBytes) | ConvertFrom-Json
    Assert-ExactProperties -Value $manifest -Expected @(
        'format_version', 'patch_id', 'created_at_utc', 'from_version',
        'target_version', 'files', 'android'
    ) -Label 'Patch manifest'
    if ($manifest.format_version -ne 1) { throw 'Unsupported application patch format.' }
    $parsedPatchId = [Guid]::Empty
    if ($manifest.patch_id -isnot [string] -or
        -not [Guid]::TryParseExact($manifest.patch_id, 'D', [ref]$parsedPatchId)) {
        throw 'Application patch ID must be a canonical UUID.'
    }
    Assert-SemanticVersion -Value $manifest.from_version -Label 'Patch source version'
    Assert-SemanticVersion -Value $manifest.target_version -Label 'Patch target version'
    if ($manifest.from_version -cne $release.version) {
        throw "This patch requires govor.ai $($manifest.from_version); installed version is $($release.version)."
    }
    if ($manifest.target_version -ceq $manifest.from_version) {
        throw 'Application patch target must differ from its source version.'
    }
    if ($manifest.files -isnot [array] -or $manifest.files.Count -lt 1 -or
        $manifest.files.Count -gt $maximumFileCount) {
        throw 'Application patch has an invalid number of host file operations.'
    }

    $expectedEntries = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    [void]$expectedEntries.Add('manifest.json')
    [void]$expectedEntries.Add('manifest.sig')
    $paths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    [long]$expandedSize = 0
    foreach ($operation in $manifest.files) {
        if ($operation.action -eq 'add') {
            Assert-ExactProperties -Value $operation -Expected @('path', 'action', 'size', 'sha256') -Label 'Add operation'
        }
        elseif ($operation.action -eq 'replace') {
            Assert-ExactProperties -Value $operation -Expected @(
                'path', 'action', 'old_size', 'old_sha256', 'size', 'sha256'
            ) -Label 'Replace operation'
        }
        elseif ($operation.action -eq 'delete') {
            Assert-ExactProperties -Value $operation -Expected @(
                'path', 'action', 'old_size', 'old_sha256'
            ) -Label 'Delete operation'
        }
        else { throw 'Application patch contains an unsupported file action.' }
        [void](Resolve-InstallPath -RelativePath ([string]$operation.path))
        if (-not $paths.Add([string]$operation.path)) {
            throw "Application patch repeats a host path: $($operation.path)"
        }
        if ($protectedPaths -icontains [string]$operation.path) {
            throw "Application patch may not replace its bootstrap or trust key: $($operation.path)"
        }
        if ($operation.action -in @('replace', 'delete')) {
            Assert-IntegerRange -Value $operation.old_size -Minimum 0 -Maximum $maximumFileBytes -Label 'Old file size'
            Assert-Sha256 -Value $operation.old_sha256 -Label 'Old file SHA-256'
        }
        if ($operation.action -in @('add', 'replace')) {
            Assert-IntegerRange -Value $operation.size -Minimum 0 -Maximum $maximumFileBytes -Label 'Payload size'
            Assert-Sha256 -Value $operation.sha256 -Label 'Payload SHA-256'
            $expandedSize += [long]$operation.size
            [void]$expectedEntries.Add("payload/$($operation.path)")
        }
    }
    $releaseOperations = @($manifest.files | Where-Object { $_.path -ieq 'config/release.json' })
    if ($releaseOperations.Count -ne 1 -or $releaseOperations[0].action -cne 'replace') {
        throw 'Application patch must replace config/release.json exactly once.'
    }

    if ($null -ne $manifest.android) {
        Assert-ExactProperties -Value $manifest.android -Expected @(
            'path', 'application_id', 'version_code', 'version_name',
            'signer_sha256', 'size', 'sha256'
        ) -Label 'Android patch metadata'
        if ($manifest.android.path -isnot [string] -or
            $manifest.android.path -cnotmatch '^android/[A-Za-z0-9._-]+\.apk$') {
            throw 'Android payload path must be a bounded APK below android/.'
        }
        if ($manifest.android.application_id -cne 'ai.govor.app') {
            throw 'Android patch application ID does not match govor.ai.'
        }
        Assert-IntegerRange -Value $manifest.android.version_code -Minimum 1 -Maximum 2100000000 -Label 'Android version code'
        if ($manifest.android.version_name -isnot [string] -or
            $manifest.android.version_name -cne $manifest.target_version) {
            throw 'Android patch version name must match the target release.'
        }
        Assert-Sha256 -Value $manifest.android.signer_sha256 -Label 'Android signer SHA-256'
        Assert-IntegerRange -Value $manifest.android.size -Minimum 1 -Maximum $maximumFileBytes -Label 'Android APK size'
        Assert-Sha256 -Value $manifest.android.sha256 -Label 'Android APK SHA-256'
        $expandedSize += [long]$manifest.android.size
        [void]$expectedEntries.Add([string]$manifest.android.path)
    }
    if ($expandedSize -gt $maximumTotalBytes) { throw 'Application patch exceeds the expanded size limit.' }
    if ($entries.Count -ne $expectedEntries.Count) { throw 'Application patch contains unlisted archive entries.' }
    foreach ($name in $entries.Keys) {
        if (-not $expectedEntries.Contains($name)) { throw "Application patch contains an unlisted entry: $name" }
    }

    $stageRoot = Join-Path $updatesRoot $manifest.patch_id
    if (Test-Path -LiteralPath $stageRoot) { throw 'This application patch ID was already staged.' }
    $payloadRoot = Join-Path $stageRoot 'payload'
    $backupRoot = Join-Path $stageRoot 'rollback'
    New-Item -ItemType Directory -Path $payloadRoot, $backupRoot | Out-Null
    foreach ($operation in $manifest.files) {
        Assert-CurrentFile -Operation $operation
        if ($operation.action -in @('add', 'replace')) {
            $staged = Join-Path $payloadRoot ([string]$operation.path).Replace('/', '\')
            Copy-ArchiveEntryChecked -Entry $entries["payload/$($operation.path)"] `
                -Destination $staged -ExpectedSize ([long]$operation.size) `
                -ExpectedSha256 ([string]$operation.sha256)
        }
    }
    $targetReleasePath = Join-Path $payloadRoot 'config\release.json'
    $targetRelease = Get-Content -LiteralPath $targetReleasePath -Raw -Encoding utf8 | ConvertFrom-Json
    Assert-ExactProperties -Value $targetRelease -Expected @('format_version', 'version', 'android') -Label 'Target release metadata'
    if ($targetRelease.format_version -ne 1 -or $targetRelease.version -cne $manifest.target_version) {
        throw 'Staged release metadata does not match the signed patch target.'
    }
    Assert-ExactProperties -Value $targetRelease.android -Expected @(
        'application_id', 'version_code', 'version_name', 'signer_sha256'
    ) -Label 'Target Android metadata'
    Assert-IntegerRange -Value $targetRelease.android.version_code -Minimum 1 -Maximum 2100000000 -Label 'Target Android version code'
    Assert-Sha256 -Value $targetRelease.android.signer_sha256 -Label 'Target Android signer SHA-256'
    if ($targetRelease.android.application_id -cne $release.android.application_id -or
        $targetRelease.android.signer_sha256 -cne $release.android.signer_sha256 -or
        $targetRelease.android.version_name -cne $manifest.target_version -or
        [long]$targetRelease.android.version_code -lt [long]$release.android.version_code) {
        throw 'Target release changes or downgrades the Android application/signing identity.'
    }
    if ($null -ne $manifest.android -and (
        $manifest.android.application_id -cne $targetRelease.android.application_id -or
        [long]$manifest.android.version_code -ne [long]$targetRelease.android.version_code -or
        $manifest.android.version_name -cne $targetRelease.android.version_name -or
        $manifest.android.signer_sha256 -cne $targetRelease.android.signer_sha256 -or
        [long]$manifest.android.version_code -le [long]$release.android.version_code
    )) {
        throw 'Android payload metadata does not match a monotonic target release.'
    }
    $stagedAndroid = $null
    if ($null -ne $manifest.android) {
        $stagedAndroid = Join-Path $stageRoot 'android-update.apk'
        Copy-ArchiveEntryChecked -Entry $entries[[string]$manifest.android.path] `
            -Destination $stagedAndroid -ExpectedSize ([long]$manifest.android.size) `
            -ExpectedSha256 ([string]$manifest.android.sha256)
    }

    # The release marker is committed last so an interrupted process never claims a target version
    # before all other operations have succeeded.
    $operations = @($manifest.files | Sort-Object @{
        Expression = { if ($_.path -ieq 'config/release.json') { 1 } else { 0 } }
    }, @{ Expression = { $_.path } })
    try {
        foreach ($operation in $operations) {
            Assert-CurrentFile -Operation $operation
            $target = Resolve-InstallPath -RelativePath ([string]$operation.path)
            $backup = Join-Path $backupRoot ([string]$operation.path).Replace('/', '\')
            if ($operation.action -in @('replace', 'delete')) {
                New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
                Copy-Item -LiteralPath $target -Destination $backup
            }
            if ($operation.action -eq 'delete') {
                [IO.File]::Delete($target)
            }
            else {
                $source = Join-Path $payloadRoot ([string]$operation.path).Replace('/', '\')
                $targetParent = Split-Path -Parent $target
                New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
                $temporaryTarget = Join-Path $targetParent ".govor-patch-$($manifest.patch_id).tmp"
                try {
                    Copy-Item -LiteralPath $source -Destination $temporaryTarget
                    if ($operation.action -eq 'replace') {
                        $discardedTarget = Join-Path $targetParent ".govor-replaced-$($manifest.patch_id).bak"
                        [IO.File]::Replace($temporaryTarget, $target, $discardedTarget)
                        [IO.File]::Delete($discardedTarget)
                    }
                    else {
                        [IO.File]::Move($temporaryTarget, $target)
                    }
                }
                finally {
                    if (Test-Path -LiteralPath $temporaryTarget -PathType Leaf) {
                        Remove-Item -LiteralPath $temporaryTarget -Force
                    }
                }
            }
            $committed.Add($operation)
        }
        if ($null -ne $manifest.android) {
            $androidRoot = Join-Path $updatesRoot 'android'
            New-Item -ItemType Directory -Force -Path $androidRoot | Out-Null
            $androidDestination = Join-Path $androidRoot ([IO.Path]::GetFileName([string]$manifest.android.path))
            Copy-Item -LiteralPath $stagedAndroid -Destination $androidDestination -Force
            if ((Get-Sha256 -Path $androidDestination) -cne [string]$manifest.android.sha256) {
                throw 'The staged Android update failed its final SHA-256 check.'
            }
        }
    }
    catch {
        $commitError = $_
        $rollbackErrors = [Collections.Generic.List[string]]::new()
        for ($index = $committed.Count - 1; $index -ge 0; $index--) {
            $operation = $committed[$index]
            $target = Resolve-InstallPath -RelativePath ([string]$operation.path)
            try {
                if ($operation.action -eq 'add') {
                    if (Test-Path -LiteralPath $target -PathType Leaf) { [IO.File]::Delete($target) }
                }
                else {
                    $backup = Join-Path $backupRoot ([string]$operation.path).Replace('/', '\')
                    $targetParent = Split-Path -Parent $target
                    New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
                    $rollbackTemp = Join-Path $targetParent ".govor-rollback-$($manifest.patch_id).tmp"
                    Copy-Item -LiteralPath $backup -Destination $rollbackTemp
                    if (Test-Path -LiteralPath $target -PathType Leaf) {
                        $discardedTarget = Join-Path $targetParent ".govor-rollback-discard-$($manifest.patch_id).bak"
                        [IO.File]::Replace($rollbackTemp, $target, $discardedTarget)
                        [IO.File]::Delete($discardedTarget)
                    }
                    else { [IO.File]::Move($rollbackTemp, $target) }
                }
            }
            catch { $rollbackErrors.Add("$($operation.path): $($_.Exception.Message)") }
        }
        if ($androidDestination -and (Test-Path -LiteralPath $androidDestination -PathType Leaf)) {
            Remove-Item -LiteralPath $androidDestination -Force
        }
        if ($rollbackErrors.Count -gt 0) {
            throw "Patch failed and rollback was incomplete: $($commitError.Exception.Message); $($rollbackErrors -join '; ')"
        }
        throw "Patch failed; all committed host changes were rolled back: $($commitError.Exception.Message)"
    }

    Write-Output "Installed signed govor.ai application patch: $($manifest.from_version) -> $($manifest.target_version)"
    Write-Output "Host operations applied: $($manifest.files.Count)"
    if ($androidDestination) {
        Write-Output "Android update verified and saved to: $androidDestination"
        Write-Output 'Copy that APK to the Android phone and open it. Android must show it as an update to ai.govor.app; approve the system installation prompt.'
        Write-Output "Expected Android signer SHA-256: $($manifest.android.signer_sha256)"
    }
}
finally {
    $archive.Dispose()
    $archiveStream.Dispose()
    if ($stageRoot -and (Test-Path -LiteralPath $stageRoot -PathType Container)) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
