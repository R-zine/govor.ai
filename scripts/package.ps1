[CmdletBinding()]
param(
    [string]$Version = '0.1.0',
    [ValidateRange(1, 2100000000)]
    [int]$VersionCode = 1,
    [string]$SigningPropertiesPath = '.secrets/android-signing.properties',
    [string]$GradleUserHome = '',
    [switch]$GradleOffline,
    [switch]$NoArchive
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$env:JAVA_HOME = Get-GovorJavaHome
$resolvedGradleUserHome = $null
if ($GradleUserHome) {
    $resolvedGradleUserHome = [IO.Path]::GetFullPath($GradleUserHome)
    $env:GRADLE_USER_HOME = $resolvedGradleUserHome
}

if ($Version -notmatch '^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$') {
    throw 'Version must be a semantic version suitable for an artifact name.'
}

$distributionRoot = [IO.Path]::GetFullPath((Join-Path $script:CacheRoot 'dist'))
$packageName = "govor.ai-$Version-windows-x64"
$stage = [IO.Path]::GetFullPath((Join-Path $distributionRoot $packageName))
if ((Split-Path -Parent $stage) -ne $distributionRoot) {
    throw 'Refusing to stage outside the repository distribution cache.'
}
if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

$signingProperties = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $SigningPropertiesPath))
if (-not (Test-Path -LiteralPath $signingProperties)) {
    throw 'Release signing is not initialized. Run ./scripts/initialize-release-signing.ps1 first.'
}

Write-Output 'Exporting the Godot release renderer...'
& (Join-Path $PSScriptRoot 'build.ps1') -Target renderer
if ($LASTEXITCODE -ne 0) { throw 'Renderer export failed.' }
if ($resolvedGradleUserHome) {
    $env:GRADLE_USER_HOME = $resolvedGradleUserHome
}

Write-Output 'Building the signed Android release APK...'
$gradle = Join-Path $script:RepositoryRoot 'apps\android\gradlew.bat'
$gradleArguments = @(
    ':app:assembleRelease',
    "-PgovorSigningProperties=$signingProperties",
    "-PgovorVersionName=$Version",
    "-PgovorVersionCode=$VersionCode"
)
if ($GradleOffline) {
    $gradleArguments += '--offline'
}
Invoke-Checked -FilePath $gradle -ArgumentList $gradleArguments -WorkingDirectory (Join-Path $script:RepositoryRoot 'apps\android')
$releaseApk = Join-Path $script:RepositoryRoot 'apps\android\app\build\outputs\apk\release\app-release.apk'
if (-not (Test-Path -LiteralPath $releaseApk)) {
    throw 'Gradle completed without the release APK.'
}
$androidSdk = Get-GovorAndroidSdk
$apkSigner = Get-ChildItem -LiteralPath (Join-Path $androidSdk 'build-tools') -Filter 'apksigner.bat' -Recurse |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $apkSigner) { throw 'Android apksigner was not found in the installed build tools.' }
Invoke-Checked -FilePath $apkSigner -ArgumentList @('verify', '--verbose', '--print-certs', $releaseApk)

Write-Output 'Copying the embedded Python runtime...'
$managedPython = Get-ChildItem -LiteralPath (Join-Path $script:ToolsRoot 'python') -Directory -Filter 'cpython-3.12.*-windows-x86_64-none' |
    Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
if (-not $managedPython) {
    throw 'The pinned CPython 3.12 runtime is missing. Run ./scripts/bootstrap.ps1 first.'
}
$runtimeRoot = Join-Path $stage 'runtime'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
Copy-Item -LiteralPath $managedPython -Destination (Join-Path $runtimeRoot 'python') -Recurse
$stagePython = Join-Path $runtimeRoot 'python\python.exe'
$requirements = Join-Path $script:CacheRoot 'release-requirements.txt'
Invoke-Checked -FilePath 'uv' -ArgumentList @(
    'export', '--frozen', '--no-dev', '--extra', 'media', '--extra', 'speech',
    '--no-emit-project', '--format', 'requirements.txt', '--output-file', $requirements
)
Invoke-Checked -FilePath 'uv' -ArgumentList @(
    'pip', 'install', '--python', $stagePython, '--break-system-packages', '--require-hashes',
    '--requirements', $requirements
)

Write-Output 'Copying application source, renderer, and local service runtimes...'
$sourceRoot = Join-Path $stage 'app'
$sourceDirectories = @(
    'apps\launcher\src', 'apps\host\src',
    'packages\domain\src', 'packages\gateway_security\src',
    'packages\provider_interfaces\src', 'packages\progress\src',
    'packages\scene_planner\src', 'packages\contracts\python',
    'services\local_ai\src', 'services\provider_router\src',
    'services\speech\src', 'services\media\src'
)
foreach ($relative in $sourceDirectories) {
    $source = Join-Path $script:RepositoryRoot $relative
    $destination = Join-Path $sourceRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse
}
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'apps\renderer\Builds\Windows') -Destination (Join-Path $stage 'renderer') -Recurse
New-Item -ItemType Directory -Force -Path (Join-Path $stage 'content') | Out-Null
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'assets\lesson-content') -Destination (Join-Path $stage 'content\lessons') -Recurse
Copy-Item -LiteralPath (Join-Path $script:ToolsRoot "llama.cpp\$($script:LlamaCppBuild)") -Destination (Join-Path $runtimeRoot 'llama.cpp') -Recurse
Copy-Item -LiteralPath (Join-Path $script:ToolsRoot "whisper.cpp\$($script:WhisperCppBuild)") -Destination (Join-Path $runtimeRoot 'whisper.cpp') -Recurse
New-Item -ItemType Directory -Force -Path (Join-Path $stage 'config') | Out-Null
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'config\release-models.json') -Destination (Join-Path $stage 'config\release-models.json')
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'config\release-sources.json') -Destination (Join-Path $stage 'config\release-sources.json')
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'config\release-notices.json') -Destination (Join-Path $stage 'config\release-notices.json')
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'distribution\windows\Start-Govor.cmd') -Destination $stage
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'distribution\windows\Setup-Govor.cmd') -Destination $stage
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'distribution\windows\Manage-Lessons.cmd') -Destination $stage
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'distribution\windows\Import-Lessons.ps1') -Destination $stage
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'distribution\windows\Install-Prerequisites.ps1') -Destination $stage

$documentation = Join-Path $stage 'documentation'
New-Item -ItemType Directory -Force -Path $documentation | Out-Null
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'docs\user-guide\windows.md') -Destination $documentation
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'docs\user-guide\android.md') -Destination $documentation
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'docs\troubleshooting\README.md') -Destination (Join-Path $documentation 'troubleshooting.md')
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'THIRD_PARTY_LICENSES.md') -Destination $documentation
Copy-Item -LiteralPath (Join-Path $script:RepositoryRoot 'distribution\GPL-COMPLIANCE.md') -Destination $documentation
Copy-Item -LiteralPath (Join-Path $runtimeRoot 'python\LICENSE.txt') -Destination (Join-Path $documentation 'PYTHON-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $script:ToolsRoot 'dotnet\LICENSE.txt') -Destination (Join-Path $documentation 'DOTNET-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $script:ToolsRoot 'dotnet\ThirdPartyNotices.txt') -Destination (Join-Path $documentation 'DOTNET-THIRD-PARTY-NOTICES.txt')
Copy-Item -LiteralPath (Join-Path $runtimeRoot 'llama.cpp\LICENSE-LLVM-OpenMP') -Destination (Join-Path $documentation 'LLAMA-CPP-LLVM-OPENMP-LICENSE.txt')

$releaseLicenses = Join-Path $documentation 'release-runtime-licenses'
New-Item -ItemType Directory -Force -Path $releaseLicenses | Out-Null
$noticeManifest = Get-Content (Join-Path $script:RepositoryRoot 'config\release-notices.json') -Raw -Encoding utf8 | ConvertFrom-Json
$noticeCache = Join-Path $script:CacheRoot 'release-notices'
New-Item -ItemType Directory -Force -Path $noticeCache | Out-Null
foreach ($notice in $noticeManifest.notices) {
    $cachedPath = Join-Path $noticeCache $notice.cache_name
    $valid = (Test-Path -LiteralPath $cachedPath) -and
        ((Get-Item -LiteralPath $cachedPath).Length -eq [long]$notice.size) -and
        ((Get-FileHash -LiteralPath $cachedPath -Algorithm SHA256).Hash.ToLowerInvariant() -eq $notice.sha256)
    if (-not $valid) {
        Invoke-WebRequest -Uri $notice.uri -OutFile $cachedPath
    }
    if ((Get-Item -LiteralPath $cachedPath).Length -ne [long]$notice.size -or
        (Get-FileHash -LiteralPath $cachedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $notice.sha256) {
        throw "Release notice failed integrity verification: $($notice.name)"
    }
    if ($notice.PSObject.Properties.Name -contains 'archive_members') {
        $extractRoot = Join-Path $noticeCache $notice.sha256
        New-Item -ItemType Directory -Force -Path $extractRoot | Out-Null
        Invoke-Checked -FilePath 'tar' -ArgumentList @('-xf', $cachedPath, '-C', $extractRoot)
        foreach ($member in $notice.archive_members) {
            $memberPath = [IO.Path]::GetFullPath((Join-Path $extractRoot $member.path))
            if (-not $memberPath.StartsWith(([IO.Path]::GetFullPath($extractRoot) + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase) -or
                -not (Test-Path -LiteralPath $memberPath -PathType Leaf)) {
                throw "Release notice archive member is missing or unsafe: $($member.path)"
            }
            Copy-Item -LiteralPath $memberPath -Destination (Join-Path $releaseLicenses $member.output_name)
        }
    }
    else {
        Copy-Item -LiteralPath $cachedPath -Destination (Join-Path $releaseLicenses $notice.output_name)
    }
}

$pythonLicenses = Join-Path $documentation 'python-package-licenses'
New-Item -ItemType Directory -Force -Path $pythonLicenses | Out-Null
Get-ChildItem -LiteralPath (Join-Path $runtimeRoot 'python\Lib\site-packages') -Directory -Filter '*.dist-info' | ForEach-Object {
    $licenseDirectory = Join-Path $_.FullName 'licenses'
    if (Test-Path -LiteralPath $licenseDirectory) {
        Copy-Item -LiteralPath $licenseDirectory -Destination (Join-Path $pythonLicenses $_.Name) -Recurse
    }
    $metadataLicenses = Get-ChildItem -LiteralPath $_.FullName -File | Where-Object {
        $_.Name -match '^(?i:license|copying|notice|copyright)'
    }
    if ($metadataLicenses) {
        $metadataDestination = Join-Path $pythonLicenses $_.Name
        New-Item -ItemType Directory -Force -Path $metadataDestination | Out-Null
        $metadataLicenses | Copy-Item -Destination $metadataDestination
    }
}

Write-Output 'Assembling corresponding source and GPL component archives...'
$sourceBundle = Join-Path $documentation 'corresponding-source\govor.ai'
New-Item -ItemType Directory -Force -Path $sourceBundle | Out-Null
$sourceFiles = & git -c safe.directory='C:/Users/PC/Documents/GitHub/govor.ai' ls-files --cached --others --exclude-standard
if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate the source bundle.' }
foreach ($relative in $sourceFiles) {
    $source = Join-Path $script:RepositoryRoot $relative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { continue }
    $destination = Join-Path $sourceBundle $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination
}

$sourceManifest = Get-Content (Join-Path $script:RepositoryRoot 'config\release-sources.json') -Raw -Encoding utf8 | ConvertFrom-Json
$upstreamSource = Join-Path $documentation 'corresponding-source\upstream'
$sourceCache = Join-Path $script:CacheRoot 'gpl-sources'
New-Item -ItemType Directory -Force -Path $upstreamSource, $sourceCache | Out-Null
foreach ($artifact in $sourceManifest.sources) {
    $cachedName = switch -Regex ($artifact.name) {
        '^piper' { 'piper-v1.8.0.tar.gz'; break }
        '^phonemizer' { 'phonemizer-v3.4.0.tar.gz'; break }
        '^espeak-ng-' { 'espeak-ng-1.52.0.tar.gz'; break }
        '^espeakng-loader' { 'espeakng-loader-0ddc87adf77e5850d7eeb542ac8a87d421b64daa.tar.gz'; break }
        default { throw "Unknown source artifact: $($artifact.name)" }
    }
    $cachedPath = Join-Path $sourceCache $cachedName
    $valid = (Test-Path -LiteralPath $cachedPath) -and
        ((Get-Item -LiteralPath $cachedPath).Length -eq [long]$artifact.size) -and
        ((Get-FileHash -LiteralPath $cachedPath -Algorithm SHA256).Hash.ToLowerInvariant() -eq $artifact.sha256)
    if (-not $valid) {
        Invoke-WebRequest -Uri $artifact.uri -OutFile $cachedPath
    }
    if ((Get-Item -LiteralPath $cachedPath).Length -ne [long]$artifact.size -or
        (Get-FileHash -LiteralPath $cachedPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $artifact.sha256) {
        throw "Corresponding source failed integrity verification: $($artifact.name)"
    }
    Copy-Item -LiteralPath $cachedPath -Destination (Join-Path $upstreamSource $artifact.name)
}

$apkOutput = Join-Path $distributionRoot "govor.ai-$Version-android-release.apk"
Copy-Item -LiteralPath $releaseApk -Destination $apkOutput -Force

$packagePythonPath = @(
    (Join-Path $sourceRoot 'apps\launcher\src'),
    (Join-Path $sourceRoot 'apps\host\src'),
    (Join-Path $sourceRoot 'packages\domain\src'),
    (Join-Path $sourceRoot 'packages\gateway_security\src'),
    (Join-Path $sourceRoot 'packages\provider_interfaces\src'),
    (Join-Path $sourceRoot 'packages\progress\src'),
    (Join-Path $sourceRoot 'packages\scene_planner\src'),
    (Join-Path $sourceRoot 'packages\contracts\python'),
    (Join-Path $sourceRoot 'services\local_ai\src'),
    (Join-Path $sourceRoot 'services\provider_router\src'),
    (Join-Path $sourceRoot 'services\speech\src'),
    (Join-Path $sourceRoot 'services\media\src')
) -join [IO.Path]::PathSeparator
$oldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $packagePythonPath
try {
    Invoke-Checked -FilePath $stagePython -ArgumentList @(
        '-c', "import govor_host.app, govor_media.app, govor_launcher.cli, govor_speech; print('GOVOR_RELEASE_IMPORTS_PASS')"
    ) -WorkingDirectory $stage
    Invoke-Checked -FilePath $stagePython -ArgumentList @(
        '-m', 'govor_launcher.cli', '--install-root', $stage, 'doctor'
    ) -WorkingDirectory $stage
    Invoke-Checked -FilePath 'cmd.exe' -ArgumentList @(
        '/d', '/c', (Join-Path $stage 'Setup-Govor.cmd'), '--doctor-only'
    ) -WorkingDirectory $stage
    Invoke-Checked -FilePath 'cmd.exe' -ArgumentList @(
        '/d', '/c', (Join-Path $stage 'Start-Govor.cmd'), '--doctor-only'
    ) -WorkingDirectory $stage
}
finally {
    $env:PYTHONPATH = $oldPythonPath
}

$artifacts = @(
    [ordered]@{
        name = $packageName
        path = $stage
        kind = 'windows-portable-directory'
    },
    [ordered]@{
        name = [IO.Path]::GetFileName($apkOutput)
        path = $apkOutput
        kind = 'signed-android-apk'
        size = (Get-Item -LiteralPath $apkOutput).Length
        sha256 = (Get-FileHash -LiteralPath $apkOutput -Algorithm SHA256).Hash.ToLowerInvariant()
    }
)

if (-not $NoArchive) {
    $archive = Join-Path $distributionRoot "$packageName.zip"
    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
    Compress-Archive -LiteralPath $stage -DestinationPath $archive -CompressionLevel Optimal
    $artifacts += [ordered]@{
        name = [IO.Path]::GetFileName($archive)
        path = $archive
        kind = 'windows-portable-archive'
        size = (Get-Item -LiteralPath $archive).Length
        sha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$manifestPath = Join-Path $distributionRoot "govor.ai-$Version-artifacts.json"
[IO.File]::WriteAllText(
    $manifestPath,
    (($artifacts | ConvertTo-Json -Depth 4) + "`n"),
    (New-Object System.Text.UTF8Encoding($false))
)
Write-Output "Release artifacts: $manifestPath"
$artifacts | ForEach-Object { Write-Output "$($_.kind): $($_.path)" }
