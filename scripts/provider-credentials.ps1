[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Set', 'Status', 'Delete')]
    [string]$Action,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z][a-z0-9._-]{1,63}$')]
    [string]$Target
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'packages\domain\src'),
    (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
    (Join-Path $script:RepositoryRoot 'packages\contracts\python'),
    (Join-Path $script:RepositoryRoot 'services\provider_router\src')
) -join [IO.Path]::PathSeparator

$arguments = @(
    'run', '--frozen', 'python', '-m', 'govor_provider_router.credential_cli',
    $Action.ToLowerInvariant(), $Target
)
if ($Action -eq 'Set') {
    $secure = Read-Host 'Provider credential' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        $plain | & uv @arguments
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        $plain = $null
    }
}
else {
    & uv @arguments
}
if ($LASTEXITCODE -ne 0) {
    throw "Credential command failed with exit code $LASTEXITCODE."
}
