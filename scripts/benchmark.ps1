[CmdletBinding()]
param(
    [ValidateSet('inventory', 'media-poc', 'local-ai')]
    [string]$Profile = 'inventory'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

if ($Profile -eq 'media-poc') {
    throw 'The media hardware benchmark is not yet implemented. No simulated performance result was generated.'
}

if ($Profile -eq 'local-ai') {
    $server = Get-GovorLlamaServer
    $llamaModel = Get-GovorLlamaModel
    $candidateModel = Get-GovorLlamaCandidateModel
    $whisperCli = Get-GovorWhisperCli
    $whisperModel = Get-GovorWhisperModel
    $output = Join-Path $script:CacheRoot 'local-ai-benchmark.json'
    $candidateOutput = Join-Path $script:CacheRoot 'local-ai-candidate-1.7b.json'
    $hostSmokeOutput = Join-Path $script:CacheRoot 'local-ai-host-smoke.json'
    $stdoutLog = Join-Path $script:CacheRoot 'llama-benchmark.stdout.log'
    $stderrLog = Join-Path $script:CacheRoot 'llama-benchmark.stderr.log'
    $candidateStdoutLog = Join-Path $script:CacheRoot 'llama-candidate.stdout.log'
    $candidateStderrLog = Join-Path $script:CacheRoot 'llama-candidate.stderr.log'
    foreach ($path in @(
        $output, $candidateOutput, $hostSmokeOutput, $stdoutLog, $stderrLog,
        $candidateStdoutLog, $candidateStderrLog
    )) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }

    $env:PYTHONPATH = @(
        (Join-Path $script:RepositoryRoot 'packages\domain\src'),
        (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
        (Join-Path $script:RepositoryRoot 'packages\contracts\python'),
        (Join-Path $script:RepositoryRoot 'services\local_ai\src'),
        (Join-Path $script:RepositoryRoot 'apps\host\src')
    ) -join [IO.Path]::PathSeparator

    $candidateProcess = Start-Process -FilePath $server -ArgumentList @(
        '-m', $candidateModel,
        '--host', '127.0.0.1', '--port', '8768',
        '-ngl', '99', '-c', '4096', '--jinja', '--no-webui', '--log-disable'
    ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $candidateStdoutLog -RedirectStandardError $candidateStderrLog
    try {
        $candidateReady = $false
        for ($attempt = 0; $attempt -lt 240; $attempt++) {
            if ($candidateProcess.HasExited) {
                throw "Qwen3 1.7B candidate exited before readiness. See $candidateStderrLog"
            }
            try {
                $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8768/health' -TimeoutSec 1
                if ($health.status -eq 'ok') { $candidateReady = $true; break }
            }
            catch { }
            Start-Sleep -Milliseconds 250
        }
        if (-not $candidateReady) { throw 'Qwen3 1.7B candidate was not ready within 60 seconds.' }
        Invoke-Checked -FilePath 'uv' -ArgumentList @(
            'run', '--frozen', 'python', 'scripts/local_ai_benchmark.py',
            '--llama-url', 'http://127.0.0.1:8768',
            '--model-id', 'qwen3-1.7b-q4_k_m',
            '--dialogue-only',
            '--whisper-executable', $whisperCli,
            '--whisper-model', $whisperModel,
            '--fixtures', 'tests/fixtures/ai/bilingual-cases.json',
            '--output', $candidateOutput
        )
        $candidateProcess.Refresh()
        $candidateMeasurements = Get-Content -LiteralPath $candidateOutput -Raw | ConvertFrom-Json
        $candidateMeasurements | Add-Member -NotePropertyName model_file_bytes -NotePropertyValue ((Get-Item -LiteralPath $candidateModel).Length)
        $candidateMeasurements | Add-Member -NotePropertyName llama_process_working_set_bytes -NotePropertyValue $candidateProcess.WorkingSet64
        $candidateMeasurements | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $candidateOutput -Encoding utf8
    }
    finally {
        if (-not $candidateProcess.HasExited) { Stop-Process -Id $candidateProcess.Id -Force }
    }

    $gpuUsedBefore = $null
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        $gpuUsedBefore = (& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
    }
    $serverProcess = Start-Process -FilePath $server -ArgumentList @(
        '-m', $llamaModel,
        '--host', '127.0.0.1', '--port', '8767',
        '-ngl', '99', '-c', '4096', '--jinja', '--no-webui', '--log-disable'
    ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    try {
        $ready = $false
        for ($attempt = 0; $attempt -lt 240; $attempt++) {
            if ($serverProcess.HasExited) {
                throw "llama.cpp exited before readiness. See $stderrLog"
            }
            try {
                $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8767/health' -TimeoutSec 1
                if ($health.status -eq 'ok') { $ready = $true; break }
            }
            catch { }
            Start-Sleep -Milliseconds 250
        }
        if (-not $ready) { throw 'llama.cpp did not become ready within 60 seconds.' }

        Invoke-Checked -FilePath 'uv' -ArgumentList @(
            'run', '--frozen', 'python', 'scripts/local_ai_benchmark.py',
            '--whisper-executable', $whisperCli,
            '--whisper-model', $whisperModel,
            '--fixtures', 'tests/fixtures/ai/bilingual-cases.json',
            '--output', $output,
            '--audio-fixture', "english-jfk|$($script:CacheRoot)\audio-fixtures\whisper-jfk.wav|en|country you",
            '--audio-fixture', "bulgarian-voxforge|$($script:CacheRoot)\audio-fixtures\voxforge-bg\dtd-20120908-cuf\wav\bg-0044.wav|bg|\u043e\u0442\u043a\u043b\u044e\u0447\u0432\u0430\u043c \u043b\u0435\u0441\u043d\u043e"
        )
        Invoke-Checked -FilePath 'uv' -ArgumentList @(
            'run', '--frozen', 'python', 'scripts/local_ai_host_smoke.py',
            '--whisper-executable', $whisperCli,
            '--whisper-model', $whisperModel,
            '--bulgarian-fixture', "$($script:CacheRoot)\audio-fixtures\voxforge-bg\dtd-20120908-cuf\wav\bg-0044.wav",
            '--english-fixture', "$($script:CacheRoot)\audio-fixtures\whisper-jfk.wav",
            '--output', $hostSmokeOutput
        )

        $serverProcess.Refresh()
        $gpuUsedAfter = $null
        if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
            $gpuUsedAfter = (& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
        }
        $measurements = Get-Content -LiteralPath $output -Raw | ConvertFrom-Json
        $candidateMeasurements = Get-Content -LiteralPath $candidateOutput -Raw | ConvertFrom-Json
        $hostSmoke = Get-Content -LiteralPath $hostSmokeOutput -Raw | ConvertFrom-Json
        $measurements | Add-Member -NotePropertyName candidate_comparison -NotePropertyValue $candidateMeasurements
        $measurements | Add-Member -NotePropertyName host_integration -NotePropertyValue $hostSmoke
        Add-Type -AssemblyName Microsoft.VisualBasic
        $computerInfo = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
        $measurements | Add-Member -NotePropertyName hardware -NotePropertyValue ([ordered]@{
            processor = $env:PROCESSOR_IDENTIFIER
            logical_processors = $env:NUMBER_OF_PROCESSORS
            system_total_memory_bytes = $computerInfo.TotalPhysicalMemory
            system_available_memory_bytes = $computerInfo.AvailablePhysicalMemory
            llama_process_working_set_bytes = $serverProcess.WorkingSet64
            llama_process_peak_working_set_bytes = $serverProcess.PeakWorkingSet64
            gpu_memory_used_before_mib = $gpuUsedBefore
            gpu_memory_used_after_mib = $gpuUsedAfter
            llama_gpu_layers_requested = 99
        })
        $measurements | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $output -Encoding utf8
        Write-Output "Local AI benchmark passed. Results: $output"
    }
    finally {
        if (-not $serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -Force }
    }
    exit 0
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
