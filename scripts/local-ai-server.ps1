[CmdletBinding()]
param(
    [int]$Port = 8767,
    [int]$GpuLayers = 99,
    [int]$ContextSize = 4096,
    [string]$ModelPath = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$server = Get-GovorLlamaServer
$model = if ($ModelPath) {
    (Resolve-Path -LiteralPath $ModelPath -ErrorAction Stop).Path
}
else {
    Get-GovorLlamaModel
}
Invoke-Checked -FilePath $server -ArgumentList @(
    '-m', $model,
    '--host', '127.0.0.1',
    '--port', $Port.ToString(),
    '-ngl', $GpuLayers.ToString(),
    '-c', $ContextSize.ToString(),
    '--jinja',
    '--no-webui',
    '--log-disable'
)
