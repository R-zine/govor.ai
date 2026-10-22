[CmdletBinding()]
param(
    [ValidateRange(30, 7200)]
    [int]$DurationSeconds = 60,
    [ValidateRange(1, 60)]
    [int]$SampleIntervalSeconds = 5,
    [string]$OutputPath = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$sdk = Get-GovorAndroidSdk
$adb = Join-Path $sdk 'platform-tools\adb.exe'
$previousErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    # ADB daemon startup writes an informational line to stderr. Do not let the repository-wide
    # Stop preference convert that harmless line into a terminating PowerShell error.
    $devices = & $adb devices -l 2>&1
    $adbExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorAction
}
if ($adbExitCode -ne 0) {
    [Console]::Error.WriteLine(
        'ADB could not start or enumerate devices. Physical-device tests were not executed.'
    )
    exit 2
}
$deviceLines = @($devices | Where-Object { $_ -match '^\S+\s+device(?:\s|$)' })
$physicalDevices = @(
    $deviceLines |
        Where-Object { $_ -notmatch '^emulator-' } |
        ForEach-Object { ($_ -split '\s+')[0] }
)
if ($physicalDevices.Count -eq 0) {
    $emulatorCount = @($deviceLines | Where-Object { $_ -match '^emulator-' }).Count
    [Console]::Error.WriteLine(
        "No authorized physical Android device is connected ($emulatorCount emulator(s) ignored). " +
        'Hardware acceptance tests were not executed.'
    )
    exit 2
}
if ($physicalDevices.Count -ne 1) {
    [Console]::Error.WriteLine(
        "Exactly one authorized physical Android device is required; found $($physicalDevices.Count)."
    )
    exit 2
}

$device = $physicalDevices[0]
$manufacturer = (& $adb -s $device shell getprop ro.product.manufacturer).Trim()
$model = (& $adb -s $device shell getprop ro.product.model).Trim()
$androidRelease = (& $adb -s $device shell getprop ro.build.version.release).Trim()
$androidApi = (& $adb -s $device shell getprop ro.build.version.sdk).Trim()
$phoneIp = (& $adb -s $device shell ip -f inet addr show wlan0 |
    Select-String -Pattern 'inet\s+(\d+\.\d+\.\d+\.\d+)' |
    ForEach-Object { $_.Matches[0].Groups[1].Value } |
    Select-Object -First 1)
if (-not $phoneIp) {
    [Console]::Error.WriteLine('The physical phone is not connected through Wi-Fi.')
    exit 2
}
$reverseMappings = @(& $adb -s $device reverse --list | Where-Object { $_.Trim() })
if ($reverseMappings.Count -ne 0) {
    [Console]::Error.WriteLine(
        'The physical phone has adb reverse mappings. Remove them before Wi-Fi acceptance.'
    )
    exit 2
}
$package = & $adb -s $device shell dumpsys package ai.govor.app
$versionName = $package |
    Select-String -Pattern 'versionName=(\S+)' |
    ForEach-Object { $_.Matches[0].Groups[1].Value } |
    Select-Object -First 1
if (-not $versionName) {
    [Console]::Error.WriteLine('The signed govor.ai Android app is not installed.')
    exit 2
}
$phoneProcessId = ((& $adb -s $device shell pidof ai.govor.app) | Out-String).Trim()
if (-not $phoneProcessId) {
    [Console]::Error.WriteLine('The signed govor.ai Android app is not running.')
    exit 2
}
if (-not (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -eq 8766 })) {
    [Console]::Error.WriteLine('The packaged media service is not listening on port 8766.')
    exit 2
}
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    [Console]::Error.WriteLine('Windows curl.exe is required for the hardware suite.')
    exit 2
}
$metricsRaw = & curl.exe --silent --show-error --fail --insecure --max-time 3 `
    'https://127.0.0.1:8766/v1/internal/metrics'
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine('The loopback-only media metrics endpoint is unavailable.')
    exit 2
}
$metrics = $metricsRaw | ConvertFrom-Json
if (-not $metrics.active -or $metrics.connection_state -ne 'connected') {
    [Console]::Error.WriteLine('The physical phone is not connected to the packaged media peer.')
    exit 2
}

Write-Output (
    "Physical hardware preflight passed: $manufacturer $model, Android $androidRelease/API " +
    "$androidApi, app $versionName, Wi-Fi IPv4 present, no adb reverse mapping."
)
$benchmarkParameters = @{
    Profile = 'media-poc'
    DurationSeconds = $DurationSeconds
    SampleIntervalSeconds = $SampleIntervalSeconds
}
if ($OutputPath) { $benchmarkParameters.OutputPath = $OutputPath }
& (Join-Path $PSScriptRoot 'benchmark.ps1') @benchmarkParameters
exit $LASTEXITCODE
