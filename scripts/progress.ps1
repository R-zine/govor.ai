[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('View', 'Export', 'Delete', 'DeleteAll')]
    [string]$Action,
    [string]$Database = 'data/progress.sqlite3',
    [string]$OutputPath,
    [switch]$ConfirmDelete
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'apps\host\src'),
    (Join-Path $script:RepositoryRoot 'packages\domain\src'),
    (Join-Path $script:RepositoryRoot 'packages\progress\src')
) -join [IO.Path]::PathSeparator
$arguments = @(
    'run', '--frozen', 'python', '-m', 'govor_host.progress_cli',
    $Action.ToLowerInvariant(), '--database', $Database
)
if ($Action -eq 'Export') {
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        throw 'Export requires -OutputPath.'
    }
    $arguments += @('--output', $OutputPath)
}
if ($Action -in @('Delete', 'DeleteAll')) {
    if (-not $ConfirmDelete) {
        throw 'Delete requires -ConfirmDelete.'
    }
    $arguments += '--confirm-delete'
    if ($Action -eq 'DeleteAll') {
        $arguments[5] = 'delete-all'
    }
}

& uv @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Progress command failed with exit code $LASTEXITCODE."
}
