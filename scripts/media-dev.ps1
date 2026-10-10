[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PairingToken,
    [switch]$AllowInsecureDevLan,
    [string]$BindHost = '0.0.0.0',
    [int]$Port = 8766,
    [ValidateSet('Diagnostic', 'Renderer')]
    [string]$Source = 'Diagnostic'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

if (-not $AllowInsecureDevLan) {
    throw 'Development signaling uses cleartext only for device feasibility and cannot satisfy Milestone 9 release acceptance. Pass -AllowInsecureDevLan explicitly on a trusted LAN.'
}
if ($PairingToken.Length -lt 32) {
    throw 'PairingToken must contain at least 32 characters.'
}

$env:GOVOR_DEV_PAIRING_TOKEN = $PairingToken
$env:GOVOR_MEDIA_SOURCE = $Source.ToLowerInvariant()
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'services\media\src'),
    (Join-Path $script:RepositoryRoot 'packages\contracts\python')
) -join [IO.Path]::PathSeparator

Write-Warning "Development feasibility server ($Source source): authenticated but NOT TLS-protected. Use only on a trusted LAN."
Invoke-Checked -FilePath 'uv' -ArgumentList @(
    'run', '--frozen', '--extra', 'media', 'uvicorn', 'govor_media.entrypoint:app',
    '--host', $BindHost, '--port', $Port.ToString()
)
