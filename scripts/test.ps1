[CmdletBinding()]
param(
    [ValidateSet('fast', 'python', 'contracts', 'kotlin', 'csharp', 'media', 'speech', 'godot', 'all', 'hardware')]
    [string]$Scope = 'fast'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$env:JAVA_HOME = Get-GovorJavaHome

function Test-Python {
    Invoke-Checked -FilePath 'uv' -ArgumentList @('run', '--frozen', '--extra', 'speech', 'ruff', 'check', '.')
    Invoke-Checked -FilePath 'uv' -ArgumentList @('run', '--frozen', '--extra', 'speech', 'ruff', 'format', '--check', '.')
    Invoke-Checked -FilePath 'uv' -ArgumentList @('run', '--frozen', '--extra', 'speech', 'mypy')
    Invoke-Checked -FilePath 'uv' -ArgumentList @('run', '--frozen', '--extra', 'speech', 'pytest', '-q', '--cov', '--cov-report=term-missing', '--cov-fail-under=85')
}

function Test-Speech {
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'speech', 'mypy',
        'services/speech/src', 'packages/provider_interfaces/src',
        'packages/contracts/python', 'packages/domain/src'
    )
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'speech', 'pytest', 'services/speech/tests', '-q'
    )
}

function Test-Contracts {
    Invoke-Checked -FilePath 'uv' -ArgumentList @('run', '--frozen', 'pytest', 'tests/contracts', '-q')
}

function Test-Kotlin {
    $gradle = Join-Path $script:RepositoryRoot 'apps\android\gradlew.bat'
    if (-not (Test-Path -LiteralPath $gradle)) {
        throw 'Gradle wrapper is missing. Run scripts/bootstrap.ps1.'
    }
    Invoke-Checked -FilePath $gradle -ArgumentList @(':core:test') -WorkingDirectory (Join-Path $script:RepositoryRoot 'apps\android')
}

function Test-CSharp {
    $dotnet = Get-GovorDotnet
    Invoke-Checked -FilePath $dotnet -ArgumentList @('test', 'packages/contracts/csharp/Govor.Contracts.Tests/Govor.Contracts.Tests.csproj', '--no-restore')
}

function Test-Media {
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'media', 'mypy',
        'services/media/src', 'packages/contracts/python'
    )
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'media', 'pytest', 'services/media/tests', '-q'
    )
}

function Test-Godot {
    $editor = Get-GovorGodotEditor
    $dotnet = Get-GovorDotnet
    $project = Join-Path $script:RepositoryRoot 'apps\renderer'
    $importLog = Join-Path $script:CacheRoot 'godot-import.log'
    $selfTestLog = Join-Path $script:CacheRoot 'godot-self-test.log'
    foreach ($log in @($importLog, $selfTestLog)) {
        if (Test-Path -LiteralPath $log) {
            Remove-Item -LiteralPath $log -Force
        }
    }

    Invoke-Checked -FilePath $editor -ArgumentList @(
        '--headless', '--editor', '--path', $project,
        '--import', '--quit', '--log-file', $importLog
    )
    Invoke-Checked -FilePath $dotnet -ArgumentList @(
        'build', (Join-Path $project 'Govor.Renderer.csproj'), '--no-restore'
    )
    Invoke-Checked -FilePath $editor -ArgumentList @(
        '--headless', '--path', $project,
        '--log-file', $selfTestLog,
        '--', '--self-test'
    )
    if (-not (Test-Path -LiteralPath $selfTestLog) -or
        -not (Select-String -LiteralPath $selfTestLog -SimpleMatch 'GOVOR_GODOT_SELF_TEST_PASS' -Quiet)) {
        throw "Godot exited without the renderer self-test marker. See $selfTestLog."
    }

    Write-Output 'Godot project import, C# build, and headless renderer self-test passed.'
}

if ($Scope -eq 'hardware') {
    & (Join-Path $PSScriptRoot 'hardware-test.ps1')
    exit $LASTEXITCODE
}

if ($Scope -in @('fast', 'python', 'all')) { Test-Python }
if ($Scope -eq 'contracts') { Test-Contracts }
if ($Scope -in @('fast', 'kotlin', 'all')) { Test-Kotlin }
if ($Scope -in @('fast', 'csharp', 'all')) { Test-CSharp }
if ($Scope -in @('media', 'all')) { Test-Media }
if ($Scope -eq 'speech') { Test-Speech }
if ($Scope -in @('godot', 'all')) { Test-Godot }

if ($Scope -eq 'all') {
    Initialize-GovorAndroidDebugKeystore
    $gradle = Join-Path $script:RepositoryRoot 'apps\android\gradlew.bat'
    Invoke-Checked -FilePath $gradle -ArgumentList @(':app:assembleDebug') -WorkingDirectory (Join-Path $script:RepositoryRoot 'apps\android')
}

Write-Output "Test scope '$Scope' passed."
