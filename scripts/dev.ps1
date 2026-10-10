[CmdletBinding()]
param(
    [ValidateSet('mock', 'production')]
    [string]$Mode = 'mock',
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8765
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

if ($Mode -eq 'production') {
    throw 'Production providers are not implemented. Use -Mode mock; do not present the fake providers as production.'
}
if ($BindHost -notin @('127.0.0.1', '::1')) {
    throw 'Mock control has no LAN authentication. It may bind only to loopback.'
}

$env:GOVOR_MODE = 'fake'
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'apps\host\src'),
    (Join-Path $script:RepositoryRoot 'packages\domain\src'),
    (Join-Path $script:RepositoryRoot 'packages\contracts\python')
) -join [IO.Path]::PathSeparator

$renderer = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
if (-not (Test-Path -LiteralPath $renderer)) {
    throw 'The renderer build is missing. Run ./scripts/build.ps1 -Target renderer first.'
}

$rendererProcess = Start-Process -FilePath $renderer -ArgumentList @(
    '--', '--no-startup-tone', '--mute-local-audio',
    "--control-url=ws://127.0.0.1:$Port/v1/renderer/control"
) -PassThru
try {
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', 'uvicorn', 'govor_host.app:app',
        '--host', $BindHost, '--port', $Port.ToString()
    )
}
finally {
    if (-not $rendererProcess.HasExited) {
        Stop-Process -Id $rendererProcess.Id -Force
    }
}
