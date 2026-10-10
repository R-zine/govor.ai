[CmdletBinding()]
param(
    [ValidateSet('inventory', 'media-poc')]
    [string]$Profile = 'inventory'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

if ($Profile -eq 'media-poc') {
    throw 'The media hardware benchmark is not yet implemented. No simulated performance result was generated.'
}

$gpu = $null
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpu = (& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null) -join "`n"
}
$result = [ordered]@{
    schema_version = '1.0'
    result_kind = 'environment_inventory'
    measured_at_utc = [DateTime]::UtcNow.ToString('o')
    hardware_performance_executed = $false
    gpu = $gpu
    note = 'Inventory only. This is not a media, model, rendering, or stability benchmark.'
}
$outputDirectory = Join-Path $script:RepositoryRoot 'docs\benchmarks\local'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$output = Join-Path $outputDirectory 'latest-inventory.json'
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $output -Encoding utf8
Write-Output "Wrote $output"
