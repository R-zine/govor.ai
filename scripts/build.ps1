[CmdletBinding()]
param(
    [ValidateSet('all', 'android', 'csharp', 'renderer')]
    [string]$Target = 'all'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$env:JAVA_HOME = Get-GovorJavaHome

if ($Target -in @('all', 'android')) {
    Initialize-GovorAndroidDebugKeystore
    Invoke-Checked -FilePath (Join-Path $script:RepositoryRoot 'apps\android\gradlew.bat') -ArgumentList @(':app:assembleDebug') -WorkingDirectory (Join-Path $script:RepositoryRoot 'apps\android')
}
if ($Target -in @('all', 'csharp')) {
    Invoke-Checked -FilePath (Get-GovorDotnet) -ArgumentList @('build', 'packages/contracts/csharp/Govor.Contracts/Govor.Contracts.csproj', '--no-restore')
}
if ($Target -in @('all', 'renderer')) {
    $editor = Get-GovorGodotEditor
    $rendererExecutable = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
    $exportLog = Join-Path $script:CacheRoot 'godot-export.log'
    if (Test-Path -LiteralPath $exportLog) {
        Remove-Item -LiteralPath $exportLog -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $rendererExecutable) | Out-Null
    Invoke-Checked -FilePath $editor -ArgumentList @(
        '--headless',
        '--path', (Join-Path $script:RepositoryRoot 'apps\renderer'),
        '--export-release', 'Windows Desktop', $rendererExecutable,
        '--log-file', $exportLog
    )
    if (-not (Test-Path -LiteralPath $rendererExecutable)) {
        throw 'Godot exited without the renderer executable. Check the export log and installed templates.'
    }
    $unexpectedErrors = @(
        Select-String -LiteralPath $exportLog -Pattern '^ERROR:' | Where-Object {
            $_.Line -ne 'ERROR: Failed to read the root certificate store.'
        }
    )
    if (-not (Test-Path -LiteralPath $exportLog) -or $unexpectedErrors.Count -gt 0) {
        throw "Godot export reported an error. See $exportLog."
    }
}
