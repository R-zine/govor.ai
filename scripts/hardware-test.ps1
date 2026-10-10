[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$sdk = Get-GovorAndroidSdk
$adb = Join-Path $sdk 'platform-tools\adb.exe'
$devices = & $adb devices -l 2>&1
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine(
        'ADB could not start or enumerate devices. Physical-device tests were not executed.'
    )
    exit 2
}
$deviceLines = @($devices | Where-Object { $_ -match '^\S+\s+device(?:\s|$)' })
$physicalDeviceLines = @($deviceLines | Where-Object { $_ -notmatch '^emulator-' })
if ($physicalDeviceLines.Count -eq 0) {
    $emulatorCount = @($deviceLines | Where-Object { $_ -match '^emulator-' }).Count
    [Console]::Error.WriteLine(
        "No authorized physical Android device is connected ($emulatorCount emulator(s) ignored). " +
        'Hardware acceptance tests were not executed.'
    )
    exit 2
}

[Console]::Error.WriteLine(
    'A device is visible, but the Milestone 9 instrumentation and 30-minute media stability ' +
    'suite are not implemented yet. Hardware acceptance tests were not executed.'
)
exit 2
