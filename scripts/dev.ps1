[CmdletBinding()]
param(
    [ValidateSet('mock', 'local')]
    [string]$Mode = 'mock',
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8765,
    [int]$MediaPort = 8766,
    [int]$LlamaPort = 8767,
    [ValidateRange(256, 32768)]
    [int]$ContextSize = 4096,
    [ValidateRange(0, 999)]
    [int]$GpuLayers = 99,
    [string]$LlamaModelPath = '',
    [string]$DialogueProviderId = 'llama.cpp-qwen3-4b-q4_k_m',
    [string]$PairingToken = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

if ($BindHost -notin @('127.0.0.1', '::1')) {
    throw 'The development control service is unauthenticated and may bind only to loopback.'
}
if ($Mode -eq 'local' -and $PairingToken.Length -lt 32) {
    throw 'Local mode requires a development PairingToken containing at least 32 characters.'
}

$renderer = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
if (-not (Test-Path -LiteralPath $renderer)) {
    throw 'The renderer build is missing. Run ./scripts/build.ps1 -Target renderer first.'
}

$env:GOVOR_MODE = $Mode
$env:GOVOR_BIND_HOST = $BindHost
$env:GOVOR_PORT = $Port.ToString()
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'apps\host\src'),
    (Join-Path $script:RepositoryRoot 'packages\domain\src'),
    (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
    (Join-Path $script:RepositoryRoot 'packages\progress\src'),
    (Join-Path $script:RepositoryRoot 'packages\scene_planner\src'),
    (Join-Path $script:RepositoryRoot 'packages\contracts\python'),
    (Join-Path $script:RepositoryRoot 'services\local_ai\src'),
    (Join-Path $script:RepositoryRoot 'services\speech\src'),
    (Join-Path $script:RepositoryRoot 'services\media\src')
) -join [IO.Path]::PathSeparator

$managedProcesses = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
try {
    if ($Mode -eq 'local') {
        $llamaServer = Get-GovorLlamaServer
        $llamaModel = if ($LlamaModelPath) {
            (Resolve-Path -LiteralPath $LlamaModelPath -ErrorAction Stop).Path
        }
        else {
            Get-GovorLlamaModel
        }
        $whisperCli = Get-GovorWhisperCli
        $whisperModel = Get-GovorWhisperModel
        $env:GOVOR_LLAMA_BASE_URL = "http://127.0.0.1:$LlamaPort"
        $env:GOVOR_DIALOGUE_PROVIDER_ID = $DialogueProviderId
        $env:GOVOR_WHISPER_EXECUTABLE = $whisperCli
        $env:GOVOR_WHISPER_MODEL = $whisperModel
        $env:GOVOR_KOKORO_MODEL = Join-Path $script:ToolsRoot 'models\speech\kokoro-v1.0.onnx'
        $env:GOVOR_KOKORO_VOICES = Join-Path $script:ToolsRoot 'models\speech\voices-v1.0.bin'
        $env:GOVOR_PIPER_BG_MODEL = Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx'
        $env:GOVOR_PIPER_BG_CONFIG = Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx.json'
        $env:GOVOR_MEDIA_CAPTURE_URL = "http://127.0.0.1:$MediaPort"
        $env:GOVOR_PROVIDER_TIMEOUT_SECONDS = '60'
        $env:GOVOR_DEV_PAIRING_TOKEN = $PairingToken
        $env:GOVOR_MEDIA_SOURCE = 'renderer'

        $llamaStdout = Join-Path $script:CacheRoot 'llama-dev.stdout.log'
        $llamaStderr = Join-Path $script:CacheRoot 'llama-dev.stderr.log'
        $mediaStdout = Join-Path $script:CacheRoot 'media-dev.stdout.log'
        $mediaStderr = Join-Path $script:CacheRoot 'media-dev.stderr.log'
        foreach ($log in @($llamaStdout, $llamaStderr, $mediaStdout, $mediaStderr)) {
            if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log -Force }
        }

        $llamaProcess = Start-Process -FilePath $llamaServer -ArgumentList @(
            '-m', $llamaModel,
            '--host', '127.0.0.1', '--port', $LlamaPort.ToString(),
            '-ngl', $GpuLayers.ToString(), '-c', $ContextSize.ToString(),
            '--jinja', '--no-webui', '--log-disable'
        ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $llamaStdout -RedirectStandardError $llamaStderr
        $managedProcesses.Add($llamaProcess)

        $uv = (Get-Command uv -ErrorAction Stop).Source
        $mediaProcess = Start-Process -FilePath $uv -ArgumentList @(
            'run', '--frozen', '--extra', 'media', '--extra', 'speech',
            'uvicorn', 'govor_media.entrypoint:app',
            '--host', '127.0.0.1', '--port', $MediaPort.ToString()
        ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $mediaStdout -RedirectStandardError $mediaStderr
        $managedProcesses.Add($mediaProcess)

        foreach ($endpoint in @(
            "http://127.0.0.1:$LlamaPort/health",
            "http://127.0.0.1:$MediaPort/health"
        )) {
            $ready = $false
            for ($attempt = 0; $attempt -lt 240; $attempt++) {
                try {
                    $health = Invoke-RestMethod -Uri $endpoint -TimeoutSec 1
                    if ($health.status -eq 'ok') { $ready = $true; break }
                }
                catch { }
                Start-Sleep -Milliseconds 250
            }
            if (-not $ready) { throw "Development service did not become ready: $endpoint" }
        }
    }

    $rendererProcess = Start-Process -FilePath $renderer -ArgumentList @(
        '--', '--no-startup-tone', '--mute-local-audio',
        "--control-url=ws://127.0.0.1:$Port/v1/renderer/control"
    ) -PassThru -WindowStyle Hidden
    $managedProcesses.Add($rendererProcess)

    Write-Output "Starting $Mode host on http://$BindHost`:$Port. Press Ctrl+C to stop all processes."
    $hostArguments = @('run', '--frozen')
    if ($Mode -eq 'local') { $hostArguments += @('--extra', 'media', '--extra', 'speech') }
    $hostArguments += @(
        'uvicorn', 'govor_host.app:app',
        '--host', $BindHost, '--port', $Port.ToString()
    )
    Invoke-Checked -FilePath 'uv' -ArgumentList $hostArguments
}
finally {
    foreach ($process in $managedProcesses) {
        $process.Refresh()
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
    Remove-Item Env:GOVOR_DEV_PAIRING_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:GOVOR_MEDIA_SOURCE -ErrorAction SilentlyContinue
}
