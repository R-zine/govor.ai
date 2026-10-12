[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$adb = Join-Path (Get-GovorAndroidSdk) 'platform-tools\adb.exe'

function Get-EmulatorUiDocument {
    $raw = (& $adb -s $script:EmulatorSerial exec-out uiautomator dump /dev/tty 2>$null) -join ''
    $endTag = '</hierarchy>'
    $endIndex = $raw.IndexOf($endTag, [StringComparison]::Ordinal)
    if ($endIndex -lt 0) {
        throw 'Android UI Automator did not return a hierarchy document.'
    }
    return [xml]$raw.Substring(0, $endIndex + $endTag.Length)
}

function Get-NodeCenter {
    param([Parameter(Mandatory = $true)]$Node)
    if ($Node.bounds -notmatch '\[(\d+),(\d+)\]\[(\d+),(\d+)\]') {
        throw "UI node has invalid bounds: $($Node.bounds)"
    }
    return @(
        [int](([int]$Matches[1] + [int]$Matches[3]) / 2),
        [int](([int]$Matches[2] + [int]$Matches[4]) / 2)
    )
}

$emulators = @(& $adb devices | Select-String '^emulator-\S+\s+device$' | ForEach-Object {
    ($_ -split '\s+')[0]
})
if ($emulators.Count -ne 1) {
    throw "Expected exactly one running Android emulator, found $($emulators.Count)."
}
$serial = $emulators[0]
$script:EmulatorSerial = $serial

$renderer = Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows\GovorRenderer.exe'
$python = Join-Path $script:RepositoryRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $renderer) -or -not (Test-Path -LiteralPath $python)) {
    throw 'Build the renderer and bootstrap media dependencies before running the emulator smoke.'
}

$token = [Guid]::NewGuid().ToString('N')
$serverStdout = Join-Path $script:CacheRoot 'godot-emulator-server.stdout.log'
$serverStderr = Join-Path $script:CacheRoot 'godot-emulator-server.stderr.log'
$controlStdout = Join-Path $script:CacheRoot 'godot-emulator-control.stdout.log'
$controlStderr = Join-Path $script:CacheRoot 'godot-emulator-control.stderr.log'
$rendererStdout = Join-Path $script:CacheRoot 'godot-emulator-renderer.stdout.log'
$rendererStderr = Join-Path $script:CacheRoot 'godot-emulator-renderer.stderr.log'
$rendererRuntimeLog = Join-Path $script:CacheRoot 'godot-emulator-renderer.runtime.log'
$webrtcLog = Join-Path $script:CacheRoot 'godot-emulator-webrtc.log'
$uiDump = Join-Path $script:CacheRoot 'godot-emulator-window.xml'
$completedTurnUiDump = Join-Path $script:CacheRoot 'godot-emulator-completed-turn.xml'
$screenshot = Join-Path $script:CacheRoot 'godot-emulator-connected.png'
foreach ($artifact in @(
    $serverStdout, $serverStderr, $controlStdout, $controlStderr,
    $rendererStdout, $rendererStderr, $rendererRuntimeLog, $webrtcLog,
    $uiDump, $completedTurnUiDump, $screenshot
)) {
    if (Test-Path -LiteralPath $artifact) {
        Remove-Item -LiteralPath $artifact -Force
    }
}

$env:GOVOR_DEV_PAIRING_TOKEN = $token
$env:GOVOR_MEDIA_SOURCE = 'renderer'
$env:PYTHONPATH = @(
    (Join-Path $script:RepositoryRoot 'services\media\src'),
    (Join-Path $script:RepositoryRoot 'packages\contracts\python')
) -join [IO.Path]::PathSeparator

$server = $null
$controlServer = $null
$rendererProcess = $null
try {
    & $adb -s $serial reverse tcp:8766 tcp:8766 | Out-Null
    & $adb -s $serial reverse tcp:8765 tcp:8765 | Out-Null
    & $adb -s $serial shell pm grant ai.govor.app android.permission.RECORD_AUDIO | Out-Null
    & $adb -s $serial logcat -c

    $server = Start-Process -FilePath $python -ArgumentList @(
        '-m', 'uvicorn', 'govor_media.entrypoint:app',
        '--host', '127.0.0.1', '--port', '8766'
    ) -RedirectStandardOutput $serverStdout -RedirectStandardError $serverStderr `
        -WindowStyle Hidden -PassThru

    $serverReady = $false
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        try {
            $client = New-Object Net.Sockets.TcpClient
            $client.Connect('127.0.0.1', 8766)
            $client.Dispose()
            $serverReady = $true
            break
        }
        catch {
            Start-Sleep -Milliseconds 100
        }
    }
    if (-not $serverReady) {
        throw "The renderer media server did not start. See $serverStderr."
    }

    $env:PYTHONPATH = @(
        (Join-Path $script:RepositoryRoot 'apps\host\src'),
        (Join-Path $script:RepositoryRoot 'packages\domain\src'),
        (Join-Path $script:RepositoryRoot 'packages\provider_interfaces\src'),
        (Join-Path $script:RepositoryRoot 'packages\scene_planner\src'),
        (Join-Path $script:RepositoryRoot 'packages\contracts\python')
    ) -join [IO.Path]::PathSeparator
    $controlServer = Start-Process -FilePath $python -ArgumentList @(
        '-m', 'uvicorn', 'govor_host.app:app',
        '--host', '127.0.0.1', '--port', '8765'
    ) -RedirectStandardOutput $controlStdout -RedirectStandardError $controlStderr `
        -WindowStyle Hidden -PassThru
    $controlReady = $false
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 1
            if ($health.status -eq 'ok') {
                $controlReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 100
        }
    }
    if (-not $controlReady) {
        throw "The session control server did not start. See $controlStderr."
    }

    & $adb -s $serial shell am force-stop ai.govor.app
    & $adb -s $serial shell am start -n ai.govor.app/.MainActivity | Out-Null
    Start-Sleep -Milliseconds 700
    $entryUi = Get-EmulatorUiDocument
    $editFields = @($entryUi.SelectNodes('//node[@class="android.widget.EditText"]'))
    if ($editFields.Count -ne 3) {
        throw "Expected media host, control host, and token fields, found $($editFields.Count)."
    }
    $tokenCenter = Get-NodeCenter -Node $editFields[2]
    & $adb -s $serial shell input tap $tokenCenter[0] $tokenCenter[1]
    & $adb -s $serial shell input text $token
    & $adb -s $serial shell input keyevent 4
    Start-Sleep -Milliseconds 250
    $entryUi = Get-EmulatorUiDocument
    $connectText = $entryUi.SelectNodes('//node') | Where-Object { $_.text -eq 'Connect' } |
        Select-Object -First 1
    if (-not $connectText) {
        throw 'The disconnected UI did not expose the Connect button.'
    }
    $connectCenter = Get-NodeCenter -Node $connectText
    & $adb -s $serial shell input tap $connectCenter[0] $connectCenter[1]

    $connectedUi = $null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        if ($candidate.SelectNodes('//node') | Where-Object { $_.text -like 'media: connected*' }) {
            $connectedUi = $candidate
            break
        }
    }
    if (-not $connectedUi) {
        throw "The emulator did not reach connected state. See $serverStderr."
    }

    $rendererProcess = Start-Process -FilePath $renderer -ArgumentList @(
        '--log-file', $rendererRuntimeLog, '--', '--mute-local-audio',
        '--control-url=ws://127.0.0.1:8765/v1/renderer/control'
    ) `
        -RedirectStandardOutput $rendererStdout -RedirectStandardError $rendererStderr `
        -WindowStyle Hidden -PassThru

    $rendererControlReady = $false
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 1
            if ($health.renderer_connected) {
                $rendererControlReady = $true
                break
            }
        }
        catch {
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not $rendererControlReady) {
        throw "Godot did not establish renderer control. See $controlStderr and $rendererStderr."
    }

    $recoveryUi = Get-EmulatorUiDocument
    $retryText = $recoveryUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Retry lesson' } | Select-Object -First 1
    if (-not $retryText) {
        throw 'The Android session client did not expose recovery after the renderer was absent.'
    }
    $retryCenter = Get-NodeCenter -Node $retryText
    & $adb -s $serial shell input tap $retryCenter[0] $retryCenter[1]

    $rendererPublications = ''
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        $rendererPublications =
            (Get-Content -LiteralPath $serverStdout -Raw -ErrorAction SilentlyContinue) +
            (Get-Content -LiteralPath $serverStderr -Raw -ErrorAction SilentlyContinue)
        if ($rendererPublications -match 'Received first renderer video frame' -and
            $rendererPublications -match 'Received first renderer audio block') {
            break
        }
        Start-Sleep -Milliseconds 100
    }
    if ($rendererPublications -notmatch 'Received first renderer video frame' -or
        $rendererPublications -notmatch 'Received first renderer audio block') {
        throw 'The media peer did not observe Godot frame and PCM publications.'
    }

    $videoLog = ''
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $videoLog = (& $adb -s $serial logcat -d -v brief 'org.webrtc.Logging:I' '*:S') -join "`n"
        if ($videoLog -match 'Reporting first rendered frame' -and
            $videoLog -match 'frame resolution changed to 1280x720') {
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if ($videoLog -notmatch 'Reporting first rendered frame' -or
        $videoLog -notmatch 'frame resolution changed to 1280x720') {
        throw 'Android WebRTC did not report its first rendered 1280x720 Godot frame.'
    }
    $lessonUi = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        if ($candidate.SelectNodes('//node') | Where-Object { $_.text -like '*Hold while speaking*' }) {
            $lessonUi = $candidate
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $lessonUi) {
        throw 'The fake teacher turn did not reach playback completion on Android.'
    }

    $ui = $lessonUi
    $ui.Save($uiDump)
    $holdText = $ui.SelectNodes('//node') | Where-Object { $_.text -like '*talk*' } |
        Select-Object -Last 1
    if (-not $holdText) {
        throw 'The connected UI did not expose the hold-to-talk control.'
    }
    $holdCenter = Get-NodeCenter -Node $holdText
    & $adb -s $serial shell input swipe $holdCenter[0] $holdCenter[1] $holdCenter[0] $holdCenter[1] 750

    $completedTurnUi = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        $hasReply = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -like 'Teacher: Thank you*' }
        $hasTranscript = $candidate.SelectNodes('//node') |
            Where-Object { $_.text -eq 'You: I would like coffee, please.' }
        if ($hasReply -and $hasTranscript) {
            $completedTurnUi = $candidate
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $completedTurnUi) {
        throw 'The Android client did not complete fake STT, dialogue, speech, and next-turn delivery.'
    }
    $completedTurnUi.Save($completedTurnUiDump)

    & $adb -s $serial shell screencap -p /sdcard/govor-godot-connected.png
    & $adb -s $serial pull /sdcard/govor-godot-connected.png $screenshot | Out-Null
    Start-Sleep -Seconds 6

    $videoLog = (& $adb -s $serial logcat -d -v brief 'org.webrtc.Logging:I' '*:S') -join "`n"
    [IO.File]::WriteAllText($webrtcLog, $videoLog + "`n", [Text.UTF8Encoding]::new($false))
    $frameStats = @($videoLog -split "`n" | Where-Object {
        $_ -match 'Frames received: [1-9]\d*'
    })
    if ($frameStats.Count -eq 0) {
        throw 'Android WebRTC did not report a positive continuous-frame interval.'
    }
    Write-Output "Latest Android frame interval: $($frameStats[-1].Trim())"

    $serverLog = (Get-Content -LiteralPath $serverStdout -Raw -ErrorAction SilentlyContinue) +
        (Get-Content -LiteralPath $serverStderr -Raw -ErrorAction SilentlyContinue)
    if ($serverLog -notmatch 'Received first renderer video frame: width=1280 height=720' -or
        $serverLog -notmatch 'Received first renderer audio block: sample_rate_hz=48000') {
        throw "The media peer did not report Godot frame and PCM publications. See $serverStderr."
    }
    if ($serverLog -notmatch 'Received first client microphone frame') {
        throw "The media peer did not report an emulator microphone frame. See $serverStderr."
    }

    $connectedUi = Get-EmulatorUiDocument
    $disconnectText = $connectedUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Disconnect' } | Select-Object -First 1
    if (-not $disconnectText) {
        throw 'The connected UI did not expose the Disconnect button.'
    }
    $disconnectCenter = Get-NodeCenter -Node $disconnectText
    & $adb -s $serial shell input tap $disconnectCenter[0] $disconnectCenter[1]

    $reconnectUi = $null
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        if ($candidate.SelectNodes('//node') | Where-Object { $_.text -eq 'Connect' }) {
            $reconnectUi = $candidate
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $reconnectUi) {
        throw 'The emulator did not return to disconnected state for the reconnect check.'
    }
    $connectText = $reconnectUi.SelectNodes('//node') |
        Where-Object { $_.text -eq 'Connect' } | Select-Object -First 1
    $connectCenter = Get-NodeCenter -Node $connectText
    & $adb -s $serial shell input tap $connectCenter[0] $connectCenter[1]

    $reconnectedUi = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $candidate = Get-EmulatorUiDocument
        if ($candidate.SelectNodes('//node') | Where-Object { $_.text -like 'media: connected*' }) {
            $reconnectedUi = $candidate
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $reconnectedUi) {
        throw 'The emulator did not reconnect while the Godot renderer remained active.'
    }

    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        $serverLog = (Get-Content -LiteralPath $serverStdout -Raw -ErrorAction SilentlyContinue) +
            (Get-Content -LiteralPath $serverStderr -Raw -ErrorAction SilentlyContinue)
        if ([regex]::Matches($serverLog, 'Received first renderer video frame').Count -ge 2) {
            break
        }
        Start-Sleep -Milliseconds 100
    }
    if ([regex]::Matches($serverLog, 'Received first renderer video frame').Count -lt 2) {
        throw 'The reconnected media peer did not receive a non-black Godot frame.'
    }

    $holdText = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $reconnectedUi = Get-EmulatorUiDocument
        $holdText = $reconnectedUi.SelectNodes('//node') |
            Where-Object { $_.text -like '*talk*' } | Select-Object -Last 1
        if ($holdText) { break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $holdText) {
        throw 'The reconnected fake lesson did not reach awaiting learner state.'
    }
    $holdCenter = Get-NodeCenter -Node $holdText
    & $adb -s $serial shell input swipe $holdCenter[0] $holdCenter[1] $holdCenter[0] $holdCenter[1] 750
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $serverLog = (Get-Content -LiteralPath $serverStdout -Raw -ErrorAction SilentlyContinue) +
            (Get-Content -LiteralPath $serverStderr -Raw -ErrorAction SilentlyContinue)
        if ([regex]::Matches($serverLog, 'Received first client microphone frame').Count -ge 2) {
            break
        }
        Start-Sleep -Milliseconds 100
    }
    if ([regex]::Matches($serverLog, 'Received first client microphone frame').Count -lt 2) {
        throw 'The reconnected media peer did not receive a hold-to-talk microphone frame.'
    }
    if ([regex]::Matches($serverLog, 'Received first renderer audio block').Count -ne 1) {
        throw 'The reconnected media peer replayed retained renderer audio after the tone stopped.'
    }
    if ($serverLog -match 'Task exception was never retrieved|Traceback|MediaStreamError') {
        throw 'The reconnect path left an unhandled media task exception.'
    }
    Write-Output 'Godot renderer video and microphone reconnect passed.'

    $rendererControlLog =
        (Get-Content -LiteralPath $rendererStdout -Raw -ErrorAction SilentlyContinue) +
        (Get-Content -LiteralPath $rendererRuntimeLog -Raw -ErrorAction SilentlyContinue)
    foreach ($action in @(
        'session_started', 'teacher_speaking', 'awaiting_learner',
        'recording', 'processing', 'reset'
    )) {
        if ($rendererControlLog -notmatch "GOVOR_RENDERER_COMMAND_APPLIED:$action") {
            throw "Godot did not acknowledge the '$action' session action. See $rendererStdout."
        }
    }
    if ($rendererControlLog -notmatch 'GOVOR_SCENE_APPLIED:cafe-ordering-v1:') {
        throw "Godot did not apply the lesson-context cafe scene. See $rendererStdout."
    }
    if ($rendererControlLog -notmatch
        'GOVOR_AVATAR_SPEECH_STARTED:source=none:energy=[1-9]\d*:visemes=0:') {
        throw "Godot did not apply the fake provider's PCM-energy avatar animation. See $rendererStdout."
    }

    $rendererErrors = @(
        Select-String -Path $rendererStderr, $rendererRuntimeLog -Pattern '^ERROR:' |
            Where-Object { $_.Line -ne 'ERROR: Failed to read the root certificate store.' }
    )
    if ($rendererErrors.Count -gt 0) {
        throw "The Godot renderer wrote runtime errors. See $rendererStderr and $rendererRuntimeLog."
    }
}
finally {
    & $adb -s $serial shell am force-stop ai.govor.app 2>$null
    & $adb -s $serial reverse --remove tcp:8766 2>$null
    & $adb -s $serial reverse --remove tcp:8765 2>$null
    foreach ($process in @($rendererProcess, $controlServer, $server)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
    Remove-Item Env:GOVOR_DEV_PAIRING_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:GOVOR_MEDIA_SOURCE -ErrorAction SilentlyContinue
}

Write-Output "Godot/media/control fake-session emulator smoke passed. Screenshot: $screenshot"
