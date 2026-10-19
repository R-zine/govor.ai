[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-StrictMode -Version Latest

$resolvedRoot = [IO.Path]::GetFullPath($InstallRoot)
$llamaServer = Join-Path $resolvedRoot 'runtime\llama.cpp\llama-server.exe'
if (-not (Test-Path -LiteralPath $llamaServer -PathType Leaf)) {
    throw "The packaged llama-server is missing: $llamaServer"
}

function Test-LlamaRuntime {
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # llama-server writes version information to stderr. Windows PowerShell 5 promotes native
        # stderr to an ErrorRecord under Stop even when the executable exits successfully.
        $ErrorActionPreference = 'Continue'
        & $llamaServer --version 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch { return $false }
    finally { $ErrorActionPreference = $previousErrorActionPreference }
}

if (Test-LlamaRuntime) {
    Write-Output 'Microsoft Visual C++ runtime: ready'
    exit 0
}

$redistributable = [ordered]@{
    version = '14.51.36247.0'
    uri = 'https://download.visualstudio.microsoft.com/download/pr/ebdab8e5-1d7b-4d9f-a11b-cbb1720c3b12/843068991DAAA1F73AD9F6239BCE4D0F6A07A51F18C37EA2A867E9BECA71295C/VC_redist.x64.exe'
    size = 18731856
    sha256 = '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c'
}

$dataRoot = Join-Path $env:LOCALAPPDATA 'govor.ai'
$downloadRoot = Join-Path $dataRoot 'downloads'
$downloadPath = Join-Path $downloadRoot "VC_redist.x64-$($redistributable.version).exe"
New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null

$downloadReady = (Test-Path -LiteralPath $downloadPath -PathType Leaf) -and
    ((Get-Item -LiteralPath $downloadPath).Length -eq [int64]$redistributable.size) -and
    ((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant() -eq
        [string]$redistributable.sha256)
if (-not $downloadReady) {
    if (Test-Path -LiteralPath $downloadPath) {
        Remove-Item -LiteralPath $downloadPath -Force
    }
    Write-Output "Downloading Microsoft Visual C++ Redistributable $($redistributable.version)..."
    Invoke-WebRequest -Uri $redistributable.uri -OutFile $downloadPath -UseBasicParsing
}

if ((Get-Item -LiteralPath $downloadPath).Length -ne [int64]$redistributable.size -or
    (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne
        [string]$redistributable.sha256) {
    throw 'The Microsoft Visual C++ Redistributable failed integrity verification.'
}
$signature = Get-AuthenticodeSignature -LiteralPath $downloadPath
if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -or
    -not $signature.SignerCertificate -or
    $signature.SignerCertificate.Subject -notmatch '^CN=Microsoft Corporation,') {
    throw 'The Microsoft Visual C++ Redistributable does not have a valid Microsoft signature.'
}

$arguments = @('/install', '/quiet', '/norestart')
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$startParameters = @{
    FilePath = $downloadPath
    ArgumentList = $arguments
    PassThru = $true
    Wait = $true
}
if (-not $isAdministrator) {
    $startParameters.Verb = 'RunAs'
}
$process = Start-Process @startParameters
if ($process.ExitCode -notin 0, 1638, 3010) {
    throw "Microsoft Visual C++ Redistributable setup failed with exit code $($process.ExitCode)."
}
if (-not (Test-LlamaRuntime)) {
    $restartNote = if ($process.ExitCode -eq 3010) { ' Restart Windows, then run setup again.' } else { '' }
    throw "llama-server still cannot load after prerequisite setup.$restartNote"
}

Remove-Item -LiteralPath $downloadPath -Force
Write-Output "Microsoft Visual C++ runtime $($redistributable.version): installed and verified"
