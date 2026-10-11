$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$script:RepositoryRoot = Split-Path -Parent $PSScriptRoot
$script:ToolsRoot = Join-Path $script:RepositoryRoot '.tools'
$script:CacheRoot = Join-Path $script:RepositoryRoot '.cache'
$script:GodotVersion = '4.7.2'
$script:GodotRelease = "$($script:GodotVersion)-stable"
$script:GodotTemplateVersion = "$($script:GodotVersion).stable.mono"
$script:LlamaCppBuild = 'b11540'
$script:WhisperCppBuild = 'b5454'

function Initialize-GovorEnvironment {
    New-Item -ItemType Directory -Force -Path $script:ToolsRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $script:CacheRoot | Out-Null
    $env:UV_CACHE_DIR = Join-Path $script:CacheRoot 'uv'
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $script:ToolsRoot 'python'
    $env:DOTNET_CLI_HOME = Join-Path $script:CacheRoot 'dotnet-home'
    $env:NUGET_PACKAGES = Join-Path $script:CacheRoot 'nuget'
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $env:DOTNET_NOLOGO = '1'
    $localDotnetRoot = Join-Path $script:ToolsRoot 'dotnet'
    $localDotnet = Join-Path $localDotnetRoot 'dotnet.exe'
    if (Test-Path -LiteralPath $localDotnet) {
        $pathEntries = $env:PATH -split [IO.Path]::PathSeparator
        if ($localDotnetRoot -notin $pathEntries) {
            $env:PATH = $localDotnetRoot + [IO.Path]::PathSeparator + $env:PATH
        }
    }
    $env:GRADLE_USER_HOME = Join-Path $script:CacheRoot 'gradle'
    $env:ANDROID_USER_HOME = Join-Path $script:CacheRoot 'android-user-home'
    New-Item -ItemType Directory -Force -Path $env:ANDROID_USER_HOME | Out-Null
}

function Get-GovorJavaHome {
    if ($env:JAVA_HOME -and (Test-Path -LiteralPath (Join-Path $env:JAVA_HOME 'bin\java.exe'))) {
        return $env:JAVA_HOME
    }
    $bundledJava = 'C:\Program Files\Android\Android Studio\jbr'
    if (Test-Path -LiteralPath (Join-Path $bundledJava 'bin\java.exe')) {
        return $bundledJava
    }
    throw 'JDK 17 was not found. Install Android Studio or set JAVA_HOME to a JDK 17 installation.'
}

function Get-GovorAndroidSdk {
    foreach ($candidate in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, (Join-Path $env:LOCALAPPDATA 'Android\Sdk'))) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    throw 'Android SDK was not found. Install SDK Platform 34 and Build Tools 34.0.0.'
}

function Get-GovorDotnet {
    $globalDotnet = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($globalDotnet) {
        return $globalDotnet.Source
    }
    $localDotnet = Join-Path $script:ToolsRoot 'dotnet\dotnet.exe'
    if (Test-Path -LiteralPath $localDotnet) {
        return $localDotnet
    }
    throw 'The .NET 8 SDK is missing. Run scripts/bootstrap.ps1.'
}

function Get-GovorGodotEditor {
    if ($env:GOVOR_GODOT_EDITOR -and (Test-Path -LiteralPath $env:GOVOR_GODOT_EDITOR)) {
        return $env:GOVOR_GODOT_EDITOR
    }

    $localRoot = Join-Path $script:ToolsRoot "godot\$($script:GodotRelease)"
    if (Test-Path -LiteralPath $localRoot) {
        $localEditor = Get-ChildItem -LiteralPath $localRoot -Filter 'Godot*_mono_win64_console.exe' -Recurse |
            Select-Object -First 1 -ExpandProperty FullName
        if ($localEditor) {
            return $localEditor
        }
    }

    foreach ($commandName in @('godot', 'godot4')) {
        $globalEditor = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($globalEditor) {
            return $globalEditor.Source
        }
    }

    throw "Godot $($script:GodotRelease) .NET was not found. Run scripts/bootstrap.ps1 -IncludeRenderer or set GOVOR_GODOT_EDITOR."
}

function Get-GovorLlamaServer {
    $root = Join-Path $script:ToolsRoot "llama.cpp\$($script:LlamaCppBuild)"
    $executable = Get-ChildItem -LiteralPath $root -Filter 'llama-server.exe' -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $executable) {
        throw 'llama.cpp server is missing. Run scripts/bootstrap.ps1 -IncludeLocalAi.'
    }
    return $executable
}

function Get-GovorWhisperCli {
    $root = Join-Path $script:ToolsRoot "whisper.cpp\$($script:WhisperCppBuild)"
    $executable = Get-ChildItem -LiteralPath $root -Filter 'whisper-cli.exe' -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $executable) {
        throw 'whisper.cpp CLI is missing. Run scripts/bootstrap.ps1 -IncludeLocalAi.'
    }
    return $executable
}

function Get-GovorLlamaModel {
    $model = Join-Path $script:ToolsRoot 'models\qwen\Qwen3-4B-Q4_K_M.gguf'
    if (-not (Test-Path -LiteralPath $model)) {
        throw 'The Qwen3 model is missing. Run scripts/bootstrap.ps1 -IncludeLocalAi.'
    }
    return $model
}

function Get-GovorLlamaCandidateModel {
    $model = Join-Path $script:ToolsRoot 'models\qwen\Qwen3-1.7B-Q4_K_M.gguf'
    if (-not (Test-Path -LiteralPath $model)) {
        throw 'The Qwen3 1.7B comparison model is missing. Run scripts/bootstrap.ps1 -IncludeLocalAi.'
    }
    return $model
}

function Get-GovorWhisperModel {
    $model = Join-Path $script:ToolsRoot 'models\whisper\ggml-small.bin'
    if (-not (Test-Path -LiteralPath $model)) {
        throw 'The multilingual Whisper model is missing. Run scripts/bootstrap.ps1 -IncludeLocalAi.'
    }
    return $model
}

function Initialize-GovorAndroidDebugKeystore {
    $keyPath = Join-Path $env:ANDROID_USER_HOME 'debug.keystore'
    if (Test-Path -LiteralPath $keyPath) {
        return
    }
    $keytool = Join-Path (Get-GovorJavaHome) 'bin\keytool.exe'
    Invoke-Checked -FilePath $keytool -ArgumentList @(
        '-genkeypair', '-keystore', $keyPath,
        '-storepass', 'android', '-alias', 'androiddebugkey', '-keypass', 'android',
        '-dname', 'CN=Android Debug,O=Android,C=US',
        '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000'
    )
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter()][string[]]$ArgumentList = @(),
        [Parameter()][string]$WorkingDirectory = $script:RepositoryRoot
    )
    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($ArgumentList -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}
