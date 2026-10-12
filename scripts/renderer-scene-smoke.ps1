[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$renderer = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
if (-not (Test-Path -LiteralPath $renderer)) {
    throw 'The exported Godot renderer is missing. Run scripts/build.ps1 -Target renderer first.'
}

$outputDirectory = Join-Path $script:CacheRoot 'renderer-scene-tour'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$stdout = Join-Path $script:CacheRoot 'godot-scene-tour.stdout.log'
$stderr = Join-Path $script:CacheRoot 'godot-scene-tour.stderr.log'
$runtimeLog = Join-Path $script:CacheRoot 'godot-scene-tour.runtime.log'
$reportPath = Join-Path $outputDirectory 'renderer-scene-tour.json'
$encodingReportPath = Join-Path $outputDirectory 'renderer-encoding.json'
$proofPaths = @(
    (Join-Path $outputDirectory '1-cafe.png'),
    (Join-Path $outputDirectory '2-supermarket.png'),
    (Join-Path $outputDirectory '3-airport.png'),
    (Join-Path $outputDirectory '4-home.png')
)
foreach ($path in @($stdout, $stderr, $runtimeLog, $reportPath, $encodingReportPath) + $proofPaths) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

$process = Start-Process -FilePath $renderer -ArgumentList @(
    '--log-file', $runtimeLog, '--', '--no-startup-tone', '--mute-local-audio',
    "--scene-tour-output=$outputDirectory"
) -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
try {
    $observedWorkingSetBytes = 0L
    $observedPeakWorkingSetBytes = 0L
    Start-Sleep -Milliseconds 250
    $process.Refresh()
    $observedWorkingSetBytes = $process.WorkingSet64
    $observedPeakWorkingSetBytes = $process.PeakWorkingSet64
    $env:PYTHONPATH = @(
        (Join-Path $script:RepositoryRoot 'services\media\src'),
        (Join-Path $script:RepositoryRoot 'packages\contracts\python')
    ) -join [IO.Path]::PathSeparator
    Invoke-Checked -FilePath 'uv' -ArgumentList @(
        'run', '--frozen', '--extra', 'media', 'python',
        'scripts/renderer_encoding_benchmark.py',
        '--output', $encodingReportPath,
        '--frames', '20'
    )
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not $process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
        $process.Refresh()
        $observedWorkingSetBytes = [Math]::Max($observedWorkingSetBytes, $process.WorkingSet64)
        $observedPeakWorkingSetBytes = [Math]::Max(
            $observedPeakWorkingSetBytes,
            $process.PeakWorkingSet64
        )
        Start-Sleep -Milliseconds 100
    }
    if (-not $process.HasExited) {
        throw 'The Godot scene tour did not finish within 20 seconds.'
    }
    $process.WaitForExit()
    $process.Refresh()

    $unexpectedErrors = @(
        Select-String -Path $stderr, $runtimeLog -Pattern '^ERROR:' |
            Where-Object { $_.Line -ne 'ERROR: Failed to read the root certificate store.' }
    )
    if ($unexpectedErrors.Count -gt 0) {
        throw "The Godot scene tour wrote runtime errors. See $stderr and $runtimeLog."
    }
    if (-not (Select-String -Path $stdout, $runtimeLog -SimpleMatch 'GOVOR_SCENE_TOUR_PASS:' -Quiet)) {
        throw 'The Godot scene tour did not emit its completion marker.'
    }
    foreach ($proofPath in $proofPaths) {
        if (-not (Test-Path -LiteralPath $proofPath)) {
            throw "The Godot scene tour did not create $proofPath."
        }
    }
    $distinctProofs = @($proofPaths | ForEach-Object {
        (Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash
    } | Sort-Object -Unique)
    if ($distinctProofs.Count -ne 4) {
        throw 'The four environment proof images are not visually distinct.'
    }
    if (-not (Test-Path -LiteralPath $reportPath)) {
        throw 'The Godot scene tour did not write its benchmark report.'
    }
    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    $encoding = Get-Content -LiteralPath $encodingReportPath -Raw | ConvertFrom-Json
    if ($report.scenes.Count -ne 4 -or $report.fallback_count -ne 0 -or
        $report.cache_growth_on_revisit -ne 0 -or $report.frame_count -lt 30 -or
        $report.video_memory_growth_on_revisit_bytes -ne 0 -or
        $encoding.frame_count -lt 20 -or $encoding.packet_count -lt 1) {
        throw 'The Godot scene tour report failed its bounded scene/cache/frame checks.'
    }
    $report.video_encoding_measured = $true
    $report | Add-Member -NotePropertyName video_encoding -NotePropertyValue $encoding
    $report | Add-Member -NotePropertyName process_working_set_bytes `
        -NotePropertyValue $observedWorkingSetBytes
    $report | Add-Member -NotePropertyName process_peak_working_set_bytes `
        -NotePropertyValue $observedPeakWorkingSetBytes
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8

    Write-Output (Get-Content -LiteralPath $reportPath -Raw)
}
finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}

Write-Output 'Godot avatar and four-environment scene tour passed.'
