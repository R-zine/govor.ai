[CmdletBinding()]
param(
    [switch]$IncludeMedia,
    [switch]$IncludeRenderer,
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
    '--locked-mode'
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
        'restore', 'apps/renderer/Govor.Renderer.csproj', '--locked-mode'
    )
}

Write-Output 'Bootstrap complete.'
Write-Output "Python: managed by uv under $($env:UV_PYTHON_INSTALL_DIR)"
Write-Output "Java: $env:JAVA_HOME"
Write-Output "Android SDK: $androidSdk"
Write-Output "dotnet: $dotnet"
