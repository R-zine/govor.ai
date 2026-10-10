[CmdletBinding()]
param(
    [switch]$Audible
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$renderer = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
if (-not (Test-Path -LiteralPath $renderer)) {
    throw 'The exported Godot renderer is missing. Run scripts/build.ps1 -Target renderer first.'
}

$stdout = Join-Path $script:CacheRoot 'godot-player.stdout.log'
$stderr = Join-Path $script:CacheRoot 'godot-player.stderr.log'
$runtimeLog = Join-Path $script:CacheRoot 'godot-player.runtime.log'
$proofImage = Join-Path $script:CacheRoot 'godot-renderer-proof.png'
foreach ($log in @($stdout, $stderr, $runtimeLog, $proofImage)) {
    if (Test-Path -LiteralPath $log) {
        Remove-Item -LiteralPath $log -Force
    }
}

$arguments = @(
    '--log-file', $runtimeLog, '--', '--exit-after-tone', "--proof-image=$proofImage"
)
if (-not $Audible) {
    $arguments += '--mute-local-audio'
}

$process = Start-Process -FilePath $renderer -ArgumentList $arguments `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
    -WindowStyle Hidden -PassThru
try {
    Start-Sleep -Milliseconds 500
    $env:PYTHONPATH = @(
        (Join-Path $script:RepositoryRoot 'services\media\src'),
        (Join-Path $script:RepositoryRoot 'packages\contracts\python')
    ) -join [IO.Path]::PathSeparator
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'media', 'python', '-m', 'govor_media.renderer_probe'
    )

    if (-not $process.WaitForExit(10000)) {
        throw 'The Godot renderer did not stop after its bounded tone window.'
    }
    $process.WaitForExit()
    $process.Refresh()

    $unexpectedErrors = @(
        Select-String -Path $stderr, $runtimeLog -Pattern '^ERROR:' |
            Where-Object { $_.Line -ne 'ERROR: Failed to read the root certificate store.' }
    )
    if ($unexpectedErrors.Count -gt 0) {
        throw "The Godot renderer wrote runtime errors. See $stderr and $runtimeLog."
    }
    if (-not (Select-String -Path $stdout, $runtimeLog -SimpleMatch 'Temporary application tone completed and stopped after two seconds.' -Quiet)) {
        throw "The Godot renderer did not confirm bounded tone shutdown. See $stdout and $runtimeLog."
    }
    if (-not (Test-Path -LiteralPath $proofImage)) {
        throw "The Godot renderer did not write its proof image. See $stdout."
    }
}
finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}

Write-Output 'Godot renderer runtime and shared-memory bridge smoke passed.'
