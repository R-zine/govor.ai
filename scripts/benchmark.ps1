[CmdletBinding()]
param(
    [ValidateSet('inventory', 'media-poc', 'local-ai', 'speech', 'renderer')]
    [string]$Profile = 'inventory',
    [ValidateRange(30, 7200)]
    [int]$DurationSeconds = 60,
    [ValidateRange(1, 60)]
    [int]$SampleIntervalSeconds = 5,
    [string]$OutputPath = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

if ($Profile -eq 'renderer') {
    $server = Get-GovorLlamaServer
    $model = Get-GovorLlamaModel
    $serverStdout = Join-Path $script:CacheRoot 'llama-renderer-concurrency.stdout.log'
    $serverStderr = Join-Path $script:CacheRoot 'llama-renderer-concurrency.stderr.log'
    $smokeStdout = Join-Path $script:CacheRoot 'renderer-concurrency-smoke.stdout.log'
    $smokeStderr = Join-Path $script:CacheRoot 'renderer-concurrency-smoke.stderr.log'
    $tourReport = Join-Path $script:CacheRoot 'renderer-scene-tour\renderer-scene-tour.json'
    $output = Join-Path $script:CacheRoot 'renderer-concurrent.json'
    foreach ($path in @($serverStdout, $serverStderr, $smokeStdout, $smokeStderr, $output)) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }

    $serverProcess = Start-Process -FilePath $server -ArgumentList @(
        '-m', $model,
        '--host', '127.0.0.1', '--port', '8767',
        '-ngl', '99', '-c', '4096', '--jinja', '--no-webui', '--log-disable'
    ) -PassThru -WindowStyle Hidden -RedirectStandardOutput $serverStdout `
        -RedirectStandardError $serverStderr
    $smokeProcess = $null
    try {
        $ready = $false
        for ($attempt = 0; $attempt -lt 240; $attempt++) {
            if ($serverProcess.HasExited) {
                throw "llama.cpp exited before renderer concurrency readiness. See $serverStderr"
            }
            try {
                $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8767/health' -TimeoutSec 1
                if ($health.status -eq 'ok') {
                    $ready = $true
                    break
                }
            }
            catch { }
            Start-Sleep -Milliseconds 250
        }
        if (-not $ready) {
            throw 'llama.cpp did not become ready within 60 seconds.'
        }

        $gpuUsedBefore = $null
        if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
            $gpuUsedBefore = (& nvidia-smi --query-gpu=memory.used `
                --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
        }
        $shell = (Get-Process -Id $PID).Path
        $smokeProcess = Start-Process -FilePath $shell -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', (Join-Path $PSScriptRoot 'renderer-scene-smoke.ps1')
        ) -WorkingDirectory $script:RepositoryRoot -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $smokeStdout -RedirectStandardError $smokeStderr
        Start-Sleep -Milliseconds 500
        if ($smokeProcess.HasExited) {
            throw "The renderer concurrency smoke exited early. See $smokeStderr"
        }

        $requestBody = @{
            model = 'local-model'
            messages = @(
                @{
                    role = 'system'
                    content = 'Reply with one short English greeting. Do not explain your answer.'
                },
                @{ role = 'user'; content = 'Greet the learner.' }
            )
            temperature = 0
            max_tokens = 32
            stream = $false
        } | ConvertTo-Json -Depth 6
        $inferenceStartedAt = [DateTime]::UtcNow
        $latenciesMs = @()
        for ($requestIndex = 0; $requestIndex -lt 2; $requestIndex++) {
            $stopwatch = [Diagnostics.Stopwatch]::StartNew()
            $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8767/v1/chat/completions' `
                -Method Post -ContentType 'application/json' -Body $requestBody -TimeoutSec 30
            $stopwatch.Stop()
            if ($null -eq $response.choices -or $response.choices.Count -lt 1) {
                throw 'The concurrent local inference response had no choices.'
            }
            $latenciesMs += $stopwatch.Elapsed.TotalMilliseconds
        }
        $inferenceFinishedAt = [DateTime]::UtcNow

        if (-not $smokeProcess.WaitForExit(30000)) {
            throw 'The concurrent renderer smoke did not finish within 30 seconds.'
        }
        $smokeProcess.WaitForExit()
        if (-not (Test-Path -LiteralPath $tourReport)) {
            throw 'The concurrent renderer smoke did not produce its report.'
        }
        $tour = Get-Content -LiteralPath $tourReport -Raw | ConvertFrom-Json
        $tourStartedAt = [DateTime]::Parse($tour.measured_at_utc).ToUniversalTime()
        $tourFinishedAt = [DateTime]::Parse($tour.measured_finished_at_utc).ToUniversalTime()
        $overlapped = $inferenceStartedAt -lt $tourFinishedAt -and `
            $inferenceFinishedAt -gt $tourStartedAt
        if (-not $overlapped) {
            throw 'Local inference and renderer measurement windows did not overlap.'
        }

        $serverProcess.Refresh()
        $gpuUsedAfter = $null
        if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
            $gpuUsedAfter = (& nvidia-smi --query-gpu=memory.used `
                --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
        }
        $result = [ordered]@{
            schema_version = '1.0'
            result_kind = 'renderer_with_local_inference'
            measured_at_utc = [DateTime]::UtcNow.ToString('o')
            overlap_verified = $overlapped
            inference_request_count = $latenciesMs.Count
            inference_latency_ms = $latenciesMs
            renderer = $tour
            hardware = [ordered]@{
                llama_process_working_set_bytes = $serverProcess.WorkingSet64
                llama_process_peak_working_set_bytes = $serverProcess.PeakWorkingSet64
                gpu_memory_used_before_mib = $gpuUsedBefore
                gpu_memory_used_after_mib = $gpuUsedAfter
                hardware_video_encoding = $false
            }
        }
        $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
        Write-Output "Concurrent renderer/local-inference benchmark passed. Results: $output"
    }
    finally {
        if ($null -ne $smokeProcess -and -not $smokeProcess.HasExited) {
            Stop-Process -Id $smokeProcess.Id -Force
        }
        if (-not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
        }
    }
    exit 0
}

if ($Profile -eq 'media-poc') {
    $sdk = Get-GovorAndroidSdk
    $adb = Join-Path $sdk 'platform-tools\adb.exe'
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $deviceOutput = & $adb devices -l 2>&1
        $adbExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
    if ($adbExitCode -ne 0) {
        throw 'ADB could not enumerate devices. No hardware measurement was produced.'
    }
    $physicalDevices = @(
        $deviceOutput |
            Where-Object { $_ -match '^\S+\s+device(?:\s|$)' -and $_ -notmatch '^emulator-' } |
            ForEach-Object { ($_ -split '\s+')[0] }
    )
    if ($physicalDevices.Count -ne 1) {
        throw "Expected exactly one authorized physical Android device; found $($physicalDevices.Count)."
    }
    $device = $physicalDevices[0]
    $phoneIp = (& $adb -s $device shell ip -f inet addr show wlan0 |
        Select-String -Pattern 'inet\s+(\d+\.\d+\.\d+\.\d+)' |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Select-Object -First 1)
    if (-not $phoneIp) {
        throw 'The physical phone has no wlan0 IPv4 address. No Wi-Fi measurement was produced.'
    }
    $phoneProcessId = ((& $adb -s $device shell pidof ai.govor.app) | Out-String).Trim()
    if (-not $phoneProcessId) {
        throw 'The signed Android app is not running on the physical phone.'
    }
    if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
        throw 'Windows curl.exe is required to query loopback-only media metrics.'
    }

    function Get-MediaMetrics {
        $raw = & curl.exe --silent --show-error --fail --insecure --max-time 3 `
            'https://127.0.0.1:8766/v1/internal/metrics'
        if ($LASTEXITCODE -ne 0) {
            throw 'The loopback media metrics endpoint is unavailable.'
        }
        return $raw | ConvertFrom-Json
    }

    function Get-Percentile([double[]]$Values, [double]$Percentile) {
        if ($Values.Count -eq 0) { return $null }
        $sorted = @($Values | Sort-Object)
        $index = [Math]::Ceiling(($Percentile / 100) * $sorted.Count) - 1
        return $sorted[[Math]::Max(0, [Math]::Min($index, $sorted.Count - 1))]
    }

    $initialMetrics = Get-MediaMetrics
    if (-not $initialMetrics.active -or $initialMetrics.connection_state -ne 'connected') {
        throw 'A connected physical WebRTC peer is required before the benchmark starts.'
    }
    $initialVideoFrames = [long]$initialMetrics.renderer_video.frames_emitted
    $initialRendererFrames = [long]$initialMetrics.renderer_video.renderer_frames
    $initialMicrophoneFrames = [long]$initialMetrics.microphone.frames_received
    $startedAt = [DateTime]::UtcNow
    $stopwatch = [Diagnostics.Stopwatch]::StartNew()
    $samples = @()
    $pingSuccesses = 0
    $pingFailures = 0
    $previousCpuSeconds = $null
    $previousSampleSeconds = 0.0
    $logicalProcessors = [Math]::Max(1, [Environment]::ProcessorCount)

    while ($stopwatch.Elapsed.TotalSeconds -lt $DurationSeconds) {
        $metrics = Get-MediaMetrics
        if (-not $metrics.active -or $metrics.connection_state -ne 'connected') {
            throw "The physical WebRTC peer disconnected at $([Math]::Round($stopwatch.Elapsed.TotalSeconds, 1)) seconds."
        }
        $listenerIds = @(
            Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.LocalPort -in 8765, 8766, 8767 } |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
        $applicationProcesses = @(
            Get-Process -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Id -in $listenerIds -or $_.ProcessName -in @('GovorRenderer', 'llama-server')
                }
        )
        $workingSetBytes = [long](($applicationProcesses | Measure-Object WorkingSet64 -Sum).Sum)
        $cpuSeconds = [double](($applicationProcesses | Measure-Object CPU -Sum).Sum)
        $cpuPercent = $null
        if ($null -ne $previousCpuSeconds) {
            $sampleElapsed = $stopwatch.Elapsed.TotalSeconds - $previousSampleSeconds
            if ($sampleElapsed -gt 0) {
                $cpuPercent = 100 * ($cpuSeconds - $previousCpuSeconds) /
                    ($sampleElapsed * $logicalProcessors)
            }
        }
        $previousCpuSeconds = $cpuSeconds
        $previousSampleSeconds = $stopwatch.Elapsed.TotalSeconds

        $gpu = $null
        if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
            $gpuLine = (& nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu `
                --format=csv,noheader,nounits 2>$null | Select-Object -First 1)
            if ($gpuLine) {
                $gpuParts = @($gpuLine -split ',' | ForEach-Object { $_.Trim() })
                $gpu = [ordered]@{
                    utilization_percent = [double]$gpuParts[0]
                    memory_used_mib = [double]$gpuParts[1]
                    temperature_c = [double]$gpuParts[2]
                }
            }
        }

        $battery = & $adb -s $device shell dumpsys battery
        $temperatureTenthsC = $battery |
            Select-String -Pattern '^\s*temperature:\s*(\d+)' |
            ForEach-Object { [double]$_.Matches[0].Groups[1].Value } |
            Select-Object -First 1
        $level = $battery |
            Select-String -Pattern '^\s*level:\s*(\d+)' |
            ForEach-Object { [int]$_.Matches[0].Groups[1].Value } |
            Select-Object -First 1
        $memInfo = & $adb -s $device shell dumpsys meminfo ai.govor.app
        $totalPssKb = $memInfo |
            Select-String -Pattern 'TOTAL\s+(\d+)' |
            ForEach-Object { [long]$_.Matches[0].Groups[1].Value } |
            Select-Object -First 1
        $ping = Test-Connection -ComputerName $phoneIp -Count 1 -ErrorAction SilentlyContinue
        $pingMs = $null
        if ($ping) {
            $pingSuccesses += 1
            $pingMs = [double]$ping.ResponseTime
        }
        else {
            $pingFailures += 1
        }
        $samples += [ordered]@{
            elapsed_seconds = [Math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
            windows_working_set_bytes = $workingSetBytes
            windows_cpu_percent = $cpuPercent
            gpu = $gpu
            android_total_pss_kib = $totalPssKb
            android_battery_level_percent = $level
            android_battery_temperature_c = if ($null -ne $temperatureTenthsC) {
                $temperatureTenthsC / 10
            } else { $null }
            wifi_ping_ms = $pingMs
            video_frames_emitted = [long]$metrics.renderer_video.frames_emitted
            renderer_frames = [long]$metrics.renderer_video.renderer_frames
            microphone_frames_received = [long]$metrics.microphone.frames_received
        }
        $remaining = $DurationSeconds - $stopwatch.Elapsed.TotalSeconds
        if ($remaining -gt 0) {
            Start-Sleep -Seconds ([Math]::Min($SampleIntervalSeconds, [Math]::Ceiling($remaining)))
        }
    }
    $stopwatch.Stop()
    $finalMetrics = Get-MediaMetrics
    $endedAt = [DateTime]::UtcNow
    $decoderEvidence = (& $adb -s $device shell dumpsys media.resource_manager |
        Select-String -Pattern 'c2\..*vp8\.decoder|hw-video-codec|current VideoDec HW' |
        Select-Object -First 20 | ForEach-Object { $_.Line.Trim() })
    $phoneManufacturer = (& $adb -s $device shell getprop ro.product.manufacturer).Trim()
    $phoneModel = (& $adb -s $device shell getprop ro.product.model).Trim()
    $androidRelease = (& $adb -s $device shell getprop ro.build.version.release).Trim()
    $androidApi = (& $adb -s $device shell getprop ro.build.version.sdk).Trim()
    $windowsWorkingSets = [double[]]@($samples | ForEach-Object { $_.windows_working_set_bytes })
    $windowsCpu = [double[]]@($samples | Where-Object { $null -ne $_.windows_cpu_percent } |
        ForEach-Object { $_.windows_cpu_percent })
    $androidPss = [double[]]@($samples | Where-Object { $null -ne $_.android_total_pss_kib } |
        ForEach-Object { $_.android_total_pss_kib })
    $pings = [double[]]@($samples | Where-Object { $null -ne $_.wifi_ping_ms } |
        ForEach-Object { $_.wifi_ping_ms })
    $gpuMemory = [double[]]@($samples | Where-Object { $null -ne $_.gpu } |
        ForEach-Object { $_.gpu.memory_used_mib })
    $gpuUtilization = [double[]]@($samples | Where-Object { $null -ne $_.gpu } |
        ForEach-Object { $_.gpu.utilization_percent })
    $videoFramesEmittedDelta =
        [long]$finalMetrics.renderer_video.frames_emitted - $initialVideoFrames
    $rendererFramesDelta =
        [long]$finalMetrics.renderer_video.renderer_frames - $initialRendererFrames
    $microphoneFramesDelta =
        [long]$finalMetrics.microphone.frames_received - $initialMicrophoneFrames
    $result = [ordered]@{
        schema_version = '1.0'
        result_kind = 'physical_media_hardware'
        measured_at_utc = $startedAt.ToString('o')
        measured_finished_at_utc = $endedAt.ToString('o')
        requested_duration_seconds = $DurationSeconds
        measured_duration_seconds = $stopwatch.Elapsed.TotalSeconds
        sample_interval_seconds = $SampleIntervalSeconds
        sample_count = $samples.Count
        phone = [ordered]@{
            manufacturer = $phoneManufacturer
            model = $phoneModel
            android_release = $androidRelease
            android_api = $androidApi
            transport = 'physical-wifi'
            hardware_decoder_evidence = $decoderEvidence
        }
        media = [ordered]@{
            video_frames_emitted_delta = $videoFramesEmittedDelta
            video_frames_emitted_fps = $videoFramesEmittedDelta / $stopwatch.Elapsed.TotalSeconds
            renderer_frames_delta = $rendererFramesDelta
            renderer_frames_fps = $rendererFramesDelta / $stopwatch.Elapsed.TotalSeconds
            microphone_frames_received_delta = $microphoneFramesDelta
            final = $finalMetrics
        }
        network = [ordered]@{
            ping_successes = $pingSuccesses
            ping_failures = $pingFailures
            ping_ms_p50 = Get-Percentile $pings 50
            ping_ms_p95 = Get-Percentile $pings 95
            ping_ms_max = if ($pings.Count) { ($pings | Measure-Object -Maximum).Maximum } else { $null }
        }
        resources = [ordered]@{
            windows_working_set_bytes_start = if ($windowsWorkingSets.Count) { $windowsWorkingSets[0] } else { $null }
            windows_working_set_bytes_end = if ($windowsWorkingSets.Count) { $windowsWorkingSets[-1] } else { $null }
            windows_working_set_bytes_max = if ($windowsWorkingSets.Count) { ($windowsWorkingSets | Measure-Object -Maximum).Maximum } else { $null }
            windows_cpu_percent_p50 = Get-Percentile $windowsCpu 50
            windows_cpu_percent_p95 = Get-Percentile $windowsCpu 95
            android_total_pss_kib_start = if ($androidPss.Count) { $androidPss[0] } else { $null }
            android_total_pss_kib_end = if ($androidPss.Count) { $androidPss[-1] } else { $null }
            android_total_pss_kib_max = if ($androidPss.Count) { ($androidPss | Measure-Object -Maximum).Maximum } else { $null }
            gpu_memory_used_mib_start = if ($gpuMemory.Count) { $gpuMemory[0] } else { $null }
            gpu_memory_used_mib_end = if ($gpuMemory.Count) { $gpuMemory[-1] } else { $null }
            gpu_memory_used_mib_max = if ($gpuMemory.Count) { ($gpuMemory | Measure-Object -Maximum).Maximum } else { $null }
            gpu_utilization_percent_p50 = Get-Percentile $gpuUtilization 50
            gpu_utilization_percent_p95 = Get-Percentile $gpuUtilization 95
        }
        samples = $samples
    }
    $output = if ($OutputPath) {
        [IO.Path]::GetFullPath($OutputPath)
    }
    else {
        Join-Path $script:CacheRoot 'media-hardware-benchmark.json'
    }
    $parent = Split-Path -Parent $output
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $output -Encoding utf8
    $minimumSustainedVideoFps = 27
    if ($result.media.video_frames_emitted_fps -lt $minimumSustainedVideoFps) {
        throw "Emitted video cadence fell below the 27 fps acceptance floor. Results: $output"
    }
    if ($result.media.renderer_frames_fps -lt $minimumSustainedVideoFps) {
        throw "Unique renderer cadence fell below the 27 fps acceptance floor. Results: $output"
    }
    if ($result.media.microphone_frames_received_delta -le 0) {
        throw "No physical microphone frames arrived during the benchmark. Results: $output"
    }
    if ($pingFailures -gt 0) {
        throw "Wi-Fi ping loss was observed. Results: $output"
    }
    Write-Output "Physical media hardware benchmark passed. Results: $output"
    exit 0
}

if ($Profile -eq 'speech') {
    $env:PYTHONPATH = @(
        (Join-Path $script:RepositoryRoot 'packages\domain\src'),
        (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
        (Join-Path $script:RepositoryRoot 'packages\progress\src'),
        (Join-Path $script:RepositoryRoot 'packages\scene_planner\src'),
        (Join-Path $script:RepositoryRoot 'packages\contracts\python'),
        (Join-Path $script:RepositoryRoot 'services\speech\src')
    ) -join [IO.Path]::PathSeparator
    $output = Join-Path $script:CacheRoot 'speech-benchmark.json'
    $samples = Join-Path $script:CacheRoot 'speech-samples'
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'speech', 'python', 'scripts/speech_benchmark.py',
        '--kokoro-model', (Join-Path $script:ToolsRoot 'models\speech\kokoro-v1.0.onnx'),
        '--kokoro-voices', (Join-Path $script:ToolsRoot 'models\speech\voices-v1.0.bin'),
        '--piper-model', (Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx'),
        '--piper-config', (Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx.json'),
        '--sample-directory', $samples,
        '--output', $output
    )
    Write-Output "Speech benchmark passed. Results: $output"
    exit 0
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
    $progressDatabase = Join-Path $script:CacheRoot 'local-ai-host-smoke-progress.sqlite3'
    $stdoutLog = Join-Path $script:CacheRoot 'llama-benchmark.stdout.log'
    $stderrLog = Join-Path $script:CacheRoot 'llama-benchmark.stderr.log'
    $candidateStdoutLog = Join-Path $script:CacheRoot 'llama-candidate.stdout.log'
    $candidateStderrLog = Join-Path $script:CacheRoot 'llama-candidate.stderr.log'
    foreach ($path in @(
        $output, $candidateOutput, $hostSmokeOutput, $stdoutLog, $stderrLog,
        $candidateStdoutLog, $candidateStderrLog, $progressDatabase
    )) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }

    $env:PYTHONPATH = @(
        (Join-Path $script:RepositoryRoot 'packages\domain\src'),
        (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
        (Join-Path $script:RepositoryRoot 'packages\progress\src'),
        (Join-Path $script:RepositoryRoot 'packages\scene_planner\src'),
        (Join-Path $script:RepositoryRoot 'packages\contracts\python'),
        (Join-Path $script:RepositoryRoot 'services\local_ai\src'),
        (Join-Path $script:RepositoryRoot 'services\provider_router\src'),
        (Join-Path $script:RepositoryRoot 'services\speech\src'),
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
        $env:GOVOR_PROGRESS_DATABASE = $progressDatabase
        Invoke-Checked -FilePath 'uv' -ArgumentList @(
            'run', '--frozen', '--extra', 'speech', 'python', 'scripts/local_ai_host_smoke.py',
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
        Remove-Item Env:GOVOR_PROGRESS_DATABASE -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $progressDatabase) {
            Remove-Item -LiteralPath $progressDatabase -Force
        }
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
