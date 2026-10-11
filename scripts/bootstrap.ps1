[CmdletBinding()]
param(
    [switch]$IncludeMedia,
    [switch]$IncludeRenderer,
    [switch]$IncludeLocalAi,
    [switch]$NoDownload
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

Write-Output 'Validating govor.ai development prerequisites...'

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    throw 'uv is required. Install it from https://docs.astral.sh/uv/ and rerun this script.'
}

if (-not $NoDownload) {
    Invoke-Checked -FilePath $uv.Source -ArgumentList @('python', 'install', '3.12')
}

$syncArguments = @('sync', '--dev')
if ($IncludeMedia) {
    $syncArguments += @('--extra', 'media')
}
if ($NoDownload) {
    $syncArguments += '--offline'
}
Invoke-Checked -FilePath $uv.Source -ArgumentList $syncArguments

$env:JAVA_HOME = Get-GovorJavaHome
$androidSdk = Get-GovorAndroidSdk
$localProperties = Join-Path $script:RepositoryRoot 'apps\android\local.properties'
$escapedSdk = $androidSdk.Replace('\', '\\')
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($localProperties, "sdk.dir=$escapedSdk`n", $utf8WithoutBom)

$wrapper = Join-Path $script:RepositoryRoot 'apps\android\gradlew.bat'
if (-not (Test-Path -LiteralPath $wrapper)) {
    if ($NoDownload) {
        throw 'Gradle wrapper is missing and -NoDownload was specified.'
    }
    $gradleVersion = '8.11.1'
    $gradleZip = Join-Path $script:CacheRoot "gradle-$gradleVersion-bin.zip"
    $gradleDirectory = Join-Path $script:ToolsRoot "gradle-$gradleVersion"
    if (-not (Test-Path -LiteralPath $gradleZip)) {
        Invoke-WebRequest -Uri "https://services.gradle.org/distributions/gradle-$gradleVersion-bin.zip" -OutFile $gradleZip
    }
    if (-not (Test-Path -LiteralPath $gradleDirectory)) {
        Expand-Archive -LiteralPath $gradleZip -DestinationPath $script:ToolsRoot -Force
    }
    $gradle = Join-Path $gradleDirectory 'bin\gradle.bat'
    Invoke-Checked -FilePath $gradle -ArgumentList @('wrapper', '--gradle-version', $gradleVersion) -WorkingDirectory (Join-Path $script:RepositoryRoot 'apps\android')
}

$dotnetPresent = $true
try {
    $dotnet = Get-GovorDotnet
}
catch {
    $dotnetPresent = $false
}
if (-not $dotnetPresent) {
    if ($NoDownload) {
        throw 'The .NET SDK is missing and -NoDownload was specified.'
    }
    $installer = Join-Path $script:CacheRoot 'dotnet-install.ps1'
    Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile $installer
    & $installer -Channel '8.0' -InstallDir (Join-Path $script:ToolsRoot 'dotnet') -NoPath
    if ($LASTEXITCODE -ne 0) {
        throw "dotnet-install.ps1 failed with exit code $LASTEXITCODE"
    }
    $dotnet = Get-GovorDotnet
}

Invoke-Checked -FilePath $dotnet -ArgumentList @(
    'restore', 'packages/contracts/csharp/Govor.Contracts.Tests/Govor.Contracts.Tests.csproj',
    '--locked-mode', '-p:NuGetAudit=false'
)

if ($IncludeRenderer) {
    $godotCache = Join-Path $script:CacheRoot 'godot'
    $godotTools = Join-Path $script:ToolsRoot "godot\$($script:GodotRelease)"
    $editorArchive = Join-Path $godotCache "Godot_v$($script:GodotRelease)_mono_win64.zip"
    $templatesArchive = Join-Path $godotCache "Godot_v$($script:GodotRelease)_mono_export_templates.tpz"
    $editorUri = "https://github.com/godotengine/godot/releases/download/$($script:GodotRelease)/Godot_v$($script:GodotRelease)_mono_win64.zip"
    $templatesUri = "https://github.com/godotengine/godot/releases/download/$($script:GodotRelease)/Godot_v$($script:GodotRelease)_mono_export_templates.tpz"
    $expectedEditorSha512 = '79229fd112b0c9cbeab82363a4ef7be18ea70f1caf86bf912789335b136fbe7e01db0053a33461438c5da1c680c17bbb10040bd09bedc51221cd4423d0367757'
    $expectedTemplatesSha512 = 'bb5c41d72370ed743660361f6228006f808ab04ca33abdc545d740b044f3fe057f32ae8cb7873a1bc86ddcd82ae683b9f6dfdfe4179852f2c0f1acde2ff6bd5a'

    New-Item -ItemType Directory -Force -Path $godotCache, $godotTools | Out-Null
    foreach ($download in @(
        @{ Path = $editorArchive; Uri = $editorUri; Hash = $expectedEditorSha512 },
        @{ Path = $templatesArchive; Uri = $templatesUri; Hash = $expectedTemplatesSha512 }
    )) {
        if (-not (Test-Path -LiteralPath $download.Path)) {
            if ($NoDownload) {
                throw "Godot artifact is missing and -NoDownload was specified: $($download.Path)"
            }
            Invoke-WebRequest -Uri $download.Uri -OutFile $download.Path
        }
        $actualHash = (Get-FileHash -LiteralPath $download.Path -Algorithm SHA512).Hash.ToLowerInvariant()
        if ($actualHash -ne $download.Hash) {
            throw "Godot artifact checksum mismatch: $($download.Path)"
        }
    }

    $editor = Get-ChildItem -LiteralPath $godotTools -Filter 'Godot*_mono_win64_console.exe' -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $editor) {
        Expand-Archive -LiteralPath $editorArchive -DestinationPath $godotTools -Force
        $editor = Get-ChildItem -LiteralPath $godotTools -Filter 'Godot*_mono_win64_console.exe' -Recurse |
            Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $editor) {
        throw "Godot editor extraction completed without an executable under $godotTools"
    }

    $editorDirectory = Split-Path -Parent $editor
    $selfContainedMarker = Join-Path $editorDirectory '_sc_'
    if (-not (Test-Path -LiteralPath $selfContainedMarker)) {
        New-Item -ItemType File -Path $selfContainedMarker | Out-Null
    }

    $templateDirectory = Join-Path $editorDirectory "editor_data\export_templates\$($script:GodotTemplateVersion)"
    $windowsTemplate = Join-Path $templateDirectory 'windows_release_x86_64.exe'
    if (-not (Test-Path -LiteralPath $windowsTemplate)) {
        New-Item -ItemType Directory -Force -Path $templateDirectory | Out-Null
        Invoke-Checked -FilePath 'tar' -ArgumentList @(
            '-xf', $templatesArchive,
            '-C', $templateDirectory,
            '--strip-components', '1'
        )
    }
    if (-not (Test-Path -LiteralPath $windowsTemplate)) {
        throw "Godot export templates were extracted but the Windows release template is missing: $windowsTemplate"
    }

    Write-Output "Godot: $editor"
    Write-Output "Godot export templates: $templateDirectory"

    Invoke-Checked -FilePath $dotnet -ArgumentList @(
        'restore', 'apps/renderer/Govor.Renderer.csproj', '--locked-mode', '-p:NuGetAudit=false'
    )
}

if ($IncludeLocalAi) {
    $artifacts = @(
        @{
            Name = 'llama.cpp Vulkan runtime'
            Path = (Join-Path $script:CacheRoot "llama-$($script:LlamaCppBuild)-win-vulkan-x64.zip")
            Uri = "https://github.com/ggml-org/llama.cpp/releases/download/$($script:LlamaCppBuild)/llama-$($script:LlamaCppBuild)-bin-win-vulkan-x64.zip"
            Hash = 'ba7ca97704999d24f2f7e7f30870d336462a6693abb4ad78a404671a6c92be83'
            Size = 33464546L
        },
        @{
            Name = 'whisper.cpp CPU runtime'
            Path = (Join-Path $script:CacheRoot "whisper-$($script:WhisperCppBuild)-win-x64.zip")
            Uri = "https://github.com/ggml-org/whisper.cpp/releases/download/$($script:WhisperCppBuild)/whisper-bin-x64.zip"
            Hash = '6ba69e3482d7826214f90a6a9c84ca07782aec1e1d0c6a7c30c994fd5d816ccb'
            Size = 8928640L
        },
        @{
            Name = 'Qwen3 4B Q4_K_M model'
            Path = (Join-Path $script:ToolsRoot 'models\qwen\Qwen3-4B-Q4_K_M.gguf')
            Uri = 'https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf?download=true'
            Hash = '7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5'
            Size = 2497280256L
        },
        @{
            Name = 'Whisper multilingual small model'
            Path = (Join-Path $script:ToolsRoot 'models\whisper\ggml-small.bin')
            Uri = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-small.bin?download=true'
            Hash = '1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b'
            Size = 487601967L
        },
        @{
            Name = 'whisper.cpp human English recording fixture'
            Path = (Join-Path $script:CacheRoot 'audio-fixtures\whisper-jfk.wav')
            Uri = 'https://raw.githubusercontent.com/ggml-org/whisper.cpp/b5454/samples/jfk.wav'
            Hash = '59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e'
            Size = 352078L
        },
        @{
            Name = 'VoxForge Bulgarian microphone fixture archive'
            Path = (Join-Path $script:CacheRoot 'audio-fixtures\dtd-20120908-cuf.tgz')
            Uri = 'https://repository.voxforge1.org/downloads/bg/Trunk/Audio/Main/16kHz_16bit/dtd-20120908-cuf.tgz'
            Hash = '820399326bf59b1a8b86f684dab31a80d5b8abf0799d64aea2012e4ba1c858b9'
            Size = 1726854L
        },
        @{
            Name = 'Qwen3 1.7B Q4_K_M comparison model'
            Path = (Join-Path $script:ToolsRoot 'models\qwen\Qwen3-1.7B-Q4_K_M.gguf')
            Uri = 'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/7fb011e9aee6e4dc7adf8430df9ea8de6a466aa3/Qwen3-1.7B-Q4_K_M.gguf?download=true'
            Hash = '228fb5627f7510b8b3516cdb6435e4b0d2a2bf330fe5b0ab19284a3570a8bb1f'
            Size = 1107408544L
        }
    )
    foreach ($artifact in $artifacts) {
        $directory = Split-Path -Parent $artifact.Path
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
        $needsDownload = -not (Test-Path -LiteralPath $artifact.Path)
        if (-not $needsDownload) {
            $needsDownload = (Get-Item -LiteralPath $artifact.Path).Length -lt $artifact.Size
        }
        if ($needsDownload) {
            if ($NoDownload) {
                throw "$($artifact.Name) is missing and -NoDownload was specified: $($artifact.Path)"
            }
            Write-Output "Downloading $($artifact.Name)..."
            $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
            if ($curl) {
                Invoke-Checked -FilePath $curl.Source -ArgumentList @(
                    '--location', '--fail', '--retry', '3',
                    '--continue-at', '-', '--output', $artifact.Path, $artifact.Uri
                )
            }
            else {
                Invoke-WebRequest -Uri $artifact.Uri -OutFile $artifact.Path
            }
        }
        $actualSize = (Get-Item -LiteralPath $artifact.Path).Length
        if ($actualSize -ne $artifact.Size) {
            throw "$($artifact.Name) size mismatch: expected $($artifact.Size), found $actualSize"
        }
        $actualHash = (Get-FileHash -LiteralPath $artifact.Path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $artifact.Hash) {
            throw "$($artifact.Name) checksum mismatch: $($artifact.Path)"
        }
    }

    $llamaDirectory = Join-Path $script:ToolsRoot "llama.cpp\$($script:LlamaCppBuild)"
    $whisperDirectory = Join-Path $script:ToolsRoot "whisper.cpp\$($script:WhisperCppBuild)"
    if (-not (Test-Path -LiteralPath $llamaDirectory)) {
        Expand-Archive -LiteralPath $artifacts[0].Path -DestinationPath $llamaDirectory
    }
    if (-not (Test-Path -LiteralPath $whisperDirectory)) {
        Expand-Archive -LiteralPath $artifacts[1].Path -DestinationPath $whisperDirectory
    }
    $bulgarianFixtureRoot = Join-Path $script:CacheRoot 'audio-fixtures\voxforge-bg'
    $bulgarianFixture = Join-Path $bulgarianFixtureRoot 'dtd-20120908-cuf\wav\bg-0044.wav'
    if (-not (Test-Path -LiteralPath $bulgarianFixture)) {
        New-Item -ItemType Directory -Force -Path $bulgarianFixtureRoot | Out-Null
        Invoke-Checked -FilePath 'tar' -ArgumentList @(
            '-xzf', $artifacts[5].Path, '-C', $bulgarianFixtureRoot
        )
    }
    $bulgarianFixtureHash = (Get-FileHash -LiteralPath $bulgarianFixture -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($bulgarianFixtureHash -ne '1dc382dc5f3452436cfc15ad092f14ee00225a5293a766f34330ae04e26ba4c4') {
        throw "Extracted VoxForge Bulgarian fixture checksum mismatch: $bulgarianFixture"
    }
    $llamaServer = Get-GovorLlamaServer
    $whisperCli = Get-GovorWhisperCli
    Write-Output "llama.cpp: $llamaServer"
    Write-Output "Qwen model: $(Get-GovorLlamaModel)"
    Write-Output "Qwen comparison model: $(Get-GovorLlamaCandidateModel)"
    Write-Output "whisper.cpp: $whisperCli"
    Write-Output "Whisper model: $(Get-GovorWhisperModel)"
    Write-Output "English microphone fixture: $($artifacts[4].Path)"
    Write-Output "Bulgarian microphone fixture: $bulgarianFixture"
}

Write-Output 'Bootstrap complete.'
Write-Output "Python: managed by uv under $($env:UV_PYTHON_INSTALL_DIR)"
Write-Output "Java: $env:JAVA_HOME"
Write-Output "Android SDK: $androidSdk"
Write-Output "dotnet: $dotnet"
