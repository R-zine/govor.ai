[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$adb = Join-Path (Get-GovorAndroidSdk) 'platform-tools\adb.exe'
$uv = (Get-Command uv -ErrorAction Stop).Source
$uvicorn = Join-Path $script:RepositoryRoot '.venv\Scripts\uvicorn.exe'

function Get-EmulatorUiDocument {
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        $raw = (& $adb -s $script:EmulatorSerial exec-out uiautomator dump /dev/tty 2>$null) -join ''
        $endTag = '</hierarchy>'
        $endIndex = $raw.IndexOf($endTag, [StringComparison]::Ordinal)
        if ($endIndex -ge 0) {
            return [xml]$raw.Substring(0, $endIndex + $endTag.Length)
        }
        Start-Sleep -Milliseconds 200
    }
    throw 'Android UI Automator did not return a hierarchy document.'
}

function Get-NodeBounds {
    param([Parameter(Mandatory = $true)]$Node)
    if ($Node.bounds -notmatch '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {
        throw "UI node has invalid bounds: $($Node.bounds)"
    }
    return @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$Matches[4])
}

function Invoke-NodeTap {
    param([Parameter(Mandatory = $true)]$Node)
    $bounds = Get-NodeBounds -Node $Node
    & $adb -s $script:EmulatorSerial shell input tap `
        ([int](($bounds[0] + $bounds[2]) / 2)) ([int](($bounds[1] + $bounds[3]) / 2))
}

function Wait-LocalPort {
    param([int]$Port, [string]$Description)
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        try {
            $client = [Net.Sockets.TcpClient]::new()
            $client.Connect('127.0.0.1', $Port)
            $client.Dispose()
            return
        }
        catch { Start-Sleep -Milliseconds 100 }
    }
    throw "$Description did not listen on port $Port."
}

$emulators = @(& $adb devices | Select-String '^emulator-\S+\s+device$' | ForEach-Object {
    ($_ -split '\s+')[0]
})
if ($emulators.Count -ne 1) {
    throw "Expected exactly one running Android emulator, found $($emulators.Count)."
}
$script:EmulatorSerial = $emulators[0]

$apk = Join-Path $script:RepositoryRoot 'apps\android\app\build\outputs\apk\debug\app-debug.apk'
$renderer = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
foreach ($required in @(
    $apk,
    $renderer,
    (Join-Path $script:ToolsRoot 'models\speech\kokoro-v1.0.onnx'),
    (Join-Path $script:ToolsRoot 'models\speech\voices-v1.0.bin'),
    (Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx'),
    (Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx.json')
)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required artifact is missing: $required" }
}

$token = [Guid]::NewGuid().ToString('N')
$mediaStdout = Join-Path $script:CacheRoot 'speech-emulator-media.stdout.log'
$mediaStderr = Join-Path $script:CacheRoot 'speech-emulator-media.stderr.log'
$controlStdout = Join-Path $script:CacheRoot 'speech-emulator-control.stdout.log'
$controlStderr = Join-Path $script:CacheRoot 'speech-emulator-control.stderr.log'
$androidLog = Join-Path $script:CacheRoot 'speech-emulator-android.log'
$rendererStdout = Join-Path $script:CacheRoot 'speech-emulator-renderer.stdout.log'
$rendererStderr = Join-Path $script:CacheRoot 'speech-emulator-renderer.stderr.log'
$rendererRuntimeLog = Join-Path $script:CacheRoot 'speech-emulator-renderer.runtime.log'
$uiDump = Join-Path $script:CacheRoot 'speech-emulator-window.xml'
$lessonUiDump = Join-Path $script:CacheRoot 'speech-emulator-lesson.xml'
foreach ($artifact in @(
    $mediaStdout, $mediaStderr, $controlStdout, $controlStderr, $androidLog, $uiDump,
    $lessonUiDump, $rendererStdout, $rendererStderr, $rendererRuntimeLog
)) {
    if (Test-Path -LiteralPath $artifact) { Remove-Item -LiteralPath $artifact -Force }
}

$env:GOVOR_DEV_PAIRING_TOKEN = $token
$env:GOVOR_MEDIA_SOURCE = 'diagnostic'
$env:GOVOR_MODE = 'local'
$env:GOVOR_RENDERER_REQUIRED = 'true'
$env:GOVOR_PROVIDER_TIMEOUT_SECONDS = '60'
$env:GOVOR_KOKORO_MODEL = Join-Path $script:ToolsRoot 'models\speech\kokoro-v1.0.onnx'
$env:GOVOR_KOKORO_VOICES = Join-Path $script:ToolsRoot 'models\speech\voices-v1.0.bin'
$env:GOVOR_PIPER_BG_MODEL = Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx'
$env:GOVOR_PIPER_BG_CONFIG = Join-Path $script:ToolsRoot 'models\speech\bg_BG-dimitar-medium.onnx.json'
$progressDatabase = Join-Path $script:CacheRoot 'emulator-speech-progress.sqlite3'
if (Test-Path -LiteralPath $progressDatabase) {
    Remove-Item -LiteralPath $progressDatabase -Force
}
$env:GOVOR_PROGRESS_DATABASE = $progressDatabase
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'apps\host\src'),
    (Join-Path $script:RepositoryRoot 'packages\domain\src'),
    (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
    (Join-Path $script:RepositoryRoot 'packages\progress\src'),
    (Join-Path $script:RepositoryRoot 'packages\scene_planner\src'),
    (Join-Path $script:RepositoryRoot 'packages\contracts\python'),
    (Join-Path $script:RepositoryRoot 'services\local_ai\src'),
    (Join-Path $script:RepositoryRoot 'services\provider_router\src'),
    (Join-Path $script:RepositoryRoot 'services\speech\src'),
    (Join-Path $script:RepositoryRoot 'services\media\src')
) -join [IO.Path]::PathSeparator

$mediaProcess = $null
$controlProcess = $null
$rendererProcess = $null
$occupiedPorts = @(Get-NetTCPConnection -State Listen -LocalPort 8765,8766 `
    -ErrorAction SilentlyContinue)
if ($occupiedPorts.Count -gt 0) {
    throw 'Speech smoke requires ports 8765 and 8766 to be free before it starts.'
}
try {
    Invoke-Checked -FilePath $uv -ArgumentList @(
        'sync', '--frozen', '--extra', 'media', '--extra', 'speech'
    )
    & $adb -s $script:EmulatorSerial reverse tcp:8766 tcp:8766 | Out-Null
    & $adb -s $script:EmulatorSerial reverse tcp:8765 tcp:8765 | Out-Null
    & $adb -s $script:EmulatorSerial shell pm grant ai.govor.app android.permission.RECORD_AUDIO |
        Out-Null
    & $adb -s $script:EmulatorSerial install -r $apk | Out-Null
    & $adb -s $script:EmulatorSerial logcat -c

    $mediaProcess = Start-Process -FilePath $uvicorn -ArgumentList @(
        'govor_media.entrypoint:app', '--host', '127.0.0.1', '--port', '8766'
    ) -WindowStyle Hidden -PassThru -RedirectStandardOutput $mediaStdout `
        -RedirectStandardError $mediaStderr
    Wait-LocalPort -Port 8766 -Description 'Speech smoke media server'

    $controlProcess = Start-Process -FilePath $uvicorn -ArgumentList @(
        'govor_host.app:app', '--host', '127.0.0.1', '--port', '8765'
    ) -WindowStyle Hidden -PassThru -RedirectStandardOutput $controlStdout `
        -RedirectStandardError $controlStderr
    Wait-LocalPort -Port 8765 -Description 'Speech smoke control server'

    $rendererProcess = Start-Process -FilePath $renderer -ArgumentList @(
        '--log-file', $rendererRuntimeLog, '--', '--mute-local-audio', '--no-startup-tone',
        '--control-url=ws://127.0.0.1:8765/v1/renderer/control'
    ) -WindowStyle Hidden -PassThru -RedirectStandardOutput $rendererStdout `
        -RedirectStandardError $rendererStderr
    $rendererReady = $false
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 1
            if ($health.renderer_connected) { $rendererReady = $true; break }
        }
        catch { }
        Start-Sleep -Milliseconds 100
    }
    if (-not $rendererReady) {
        throw "Godot did not establish renderer control. See $rendererStderr."
    }

    & $adb -s $script:EmulatorSerial shell am force-stop ai.govor.app
    & $adb -s $script:EmulatorSerial shell am start -n ai.govor.app/.MainActivity | Out-Null
    Start-Sleep -Milliseconds 800
    $entryUi = Get-EmulatorUiDocument
    $editFields = @($entryUi.SelectNodes('//node[@class="android.widget.EditText"]'))
    if ($editFields.Count -ne 3) { throw 'The Android connection form was not available.' }
    Invoke-NodeTap -Node $editFields[2]
    & $adb -s $script:EmulatorSerial shell input text $token
    & $adb -s $script:EmulatorSerial shell input keyevent 4
    Start-Sleep -Milliseconds 200
    $entryUi = Get-EmulatorUiDocument
    $connect = $entryUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Connect and load lessons' } | Select-Object -First 1
    if (-not $connect) { throw 'The Android connection form had no catalog connection button.' }
    Invoke-NodeTap -Node $connect

    $catalogUi = $null
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        $connected = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -like 'media: connected*' }
        $startLesson = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -eq 'Start lesson' } | Select-Object -First 1
        if ($connected -and $startLesson) { $catalogUi = $candidate; break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $catalogUi) {
        throw "The Android client did not load the host lesson catalog. See $controlStderr."
    }
    $startLesson = $catalogUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Start lesson' } | Select-Object -First 1
    Invoke-NodeTap -Node $startLesson

    $lessonUi = $null
    for ($attempt = 0; $attempt -lt 200; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        $connected = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -like 'media: connected*' }
        $awaiting = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -eq 'Hold while speaking' }
        $teacher = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -like 'Teacher: *' }
        if ($connected -and $awaiting -and $teacher) { $lessonUi = $candidate; break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $lessonUi) {
        throw "Real teacher speech did not complete on Android. See $controlStderr."
    }
    $lessonUi.Save($lessonUiDump)

    $slow = $lessonUi.SelectNodes('//node') |
        Where-Object { $_.text -like '0.75*' } | Select-Object -First 1
    if (-not $slow) { throw 'The 0.75x speech control was not available.' }
    Invoke-NodeTap -Node $slow
    Start-Sleep -Milliseconds 300
    $controlsUi = Get-EmulatorUiDocument
    $replay = $controlsUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Replay' } | Select-Object -First 1
    if (-not $replay) { throw 'The speech replay control was not available.' }
    Invoke-NodeTap -Node $replay

    for ($attempt = 0; $attempt -lt 200; $attempt++) {
        $speechLog = (& $adb -s $script:EmulatorSerial logcat -d -v brief 'GovorSpeech:I' '*:S') -join "`n"
        if ($speechLog -match 'playback_rate=0.75' -and
            $speechLog -match 'teacher_complete notify_host=false') { break }
        Start-Sleep -Milliseconds 200
    }
    if ($speechLog -notmatch 'playback_rate=0.75' -or
        $speechLog -notmatch 'teacher_complete notify_host=false') {
        throw 'Slow replay did not complete on Android.'
    }

    $wordUi = Get-EmulatorUiDocument
    $wordButton = $wordUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Welcome' } | Select-Object -First 1
    if (-not $wordButton) { throw 'The Android word-selection buttons were not available.' }
    Invoke-NodeTap -Node $wordButton
    Start-Sleep -Milliseconds 500
    $speechLog = (& $adb -s $script:EmulatorSerial logcat -d -v brief 'GovorSpeech:I' '*:S') -join "`n"
    if ($speechLog -notmatch 'word_selected word_index=') {
        throw 'The Android word-selection interaction did not produce a selection.'
    }
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        $speechLog = (& $adb -s $script:EmulatorSerial logcat -d -v brief 'GovorSpeech:I' '*:S') -join "`n"
        if ($speechLog -match 'word_complete word_index=') { break }
        Start-Sleep -Milliseconds 200
    }
    if ($speechLog -notmatch 'word_complete word_index=') {
        throw 'Isolated word audio did not complete on Android.'
    }
    foreach ($requiredMarker in @(
        'teacher_start provider=kokoro-onnx-v1.0',
        'alignment=true',
        'highlight word_index=',
        'teacher_complete notify_host=true',
        'word_start provider='
    )) {
        if ($speechLog -notmatch [regex]::Escape($requiredMarker)) {
            throw "Android speech evidence is missing: $requiredMarker"
        }
    }
    $rendererControlLog =
        (Get-Content -LiteralPath $rendererStdout -Raw -ErrorAction SilentlyContinue) +
        (Get-Content -LiteralPath $rendererRuntimeLog -Raw -ErrorAction SilentlyContinue)
    if ($rendererControlLog -notmatch 'GOVOR_SCENE_APPLIED:cafe-ordering-v1:') {
        throw "Godot did not apply the real lesson's cafe scene. See $rendererStdout."
    }
    if ($rendererControlLog -notmatch
        'GOVOR_AVATAR_SPEECH_STARTED:source=provider_phoneme_alignment:energy=[1-9]\d*:visemes=[1-9]\d*:') {
        throw "Real provider phoneme timing did not reach the Godot avatar. See $rendererStdout."
    }
    $rendererErrors = @(
        Select-String -Path $rendererStderr, $rendererRuntimeLog -Pattern '^ERROR:' |
            Where-Object { $_.Line -ne 'ERROR: Failed to read the root certificate store.' }
    )
    if ($rendererErrors.Count -gt 0) {
        throw "Godot wrote runtime errors during real speech playback. See $rendererRuntimeLog."
    }
    [IO.File]::WriteAllText($androidLog, $speechLog + "`n", [Text.UTF8Encoding]::new($false))
    (Get-EmulatorUiDocument).Save($uiDump)
    Write-Output 'Real Kokoro audio, model timing highlights, Godot visemes, isolated-word playback, and 0.75x replay passed on the Android emulator.'
    Write-Output "Android speech log: $androidLog"
}
finally {
    & $adb -s $script:EmulatorSerial shell am force-stop ai.govor.app 2>$null
    foreach ($process in @($rendererProcess, $controlProcess, $mediaProcess)) {
        if ($null -ne $process) {
            $process.Refresh()
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    & $adb -s $script:EmulatorSerial reverse --remove tcp:8765 2>$null | Out-Null
    & $adb -s $script:EmulatorSerial reverse --remove tcp:8766 2>$null | Out-Null
    foreach ($name in @(
        'GOVOR_DEV_PAIRING_TOKEN', 'GOVOR_MEDIA_SOURCE', 'GOVOR_MODE',
        'GOVOR_RENDERER_REQUIRED', 'GOVOR_PROVIDER_TIMEOUT_SECONDS',
        'GOVOR_KOKORO_MODEL', 'GOVOR_KOKORO_VOICES', 'GOVOR_PIPER_BG_MODEL',
        'GOVOR_PIPER_BG_CONFIG', 'GOVOR_PROGRESS_DATABASE'
    )) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $progressDatabase) {
        Remove-Item -LiteralPath $progressDatabase -Force
    }
}
