[CmdletBinding()]
param(
    [switch] $ListOnly,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $ChangedFiles = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$scopes = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$androidBuild = $false
$runAll = $false

function Add-Scope {
    param([Parameter(Mandatory = $true)][string] $Name)
    [void] $script:scopes.Add($Name)
}

foreach ($rawPath in $ChangedFiles) {
    $path = $rawPath.Replace('\', '/')
    if ($path.StartsWith('./', [StringComparison]::Ordinal)) {
        $path = $path.Substring(2)
    }
    $path = $path.ToLowerInvariant()

    if ($path -match '^(docs/|readme\.md$|agents\.md$|third_party_licenses\.md$|license)') {
        continue
    }

    if ($path -match '^\.github/workflows/' -or
        $path -match '^\.pre-commit-config\.yaml$' -or
        $path -match '^(pyproject\.toml|uv\.lock)$' -or
        $path -match '^scripts/(common|test|build|bootstrap|pre-commit-tests)\.ps1$') {
        $runAll = $true
        continue
    }

    if ($path -match '^(packages/contracts/schemas/|tests/contracts/|tests/fixtures/contracts/)') {
        $runAll = $true
        continue
    }

    if ($path -match '^apps/android/' -or
        $path -match '^(gradle/|gradlew|gradlew\.bat$|settings\.gradle|build\.gradle)') {
        Add-Scope 'kotlin'
        $androidBuild = $true
        continue
    }

    if ($path -match '^apps/renderer/') {
        Add-Scope 'godot'
        continue
    }

    if ($path -match '^packages/contracts/csharp/') {
        Add-Scope 'csharp'
        Add-Scope 'godot'
        continue
    }

    if ($path -match '^services/media/') {
        Add-Scope 'media'
        continue
    }

    if ($path -match '^services/speech/') {
        Add-Scope 'speech'
        continue
    }

    if ($path -match '^packages/contracts/python/' -or
        $path -match '^packages/gateway_security/') {
        Add-Scope 'python'
        Add-Scope 'media'
        continue
    }

    if ($path -match '^(apps/host/|apps/launcher/|packages/domain/|packages/progress/|' +
        'packages/provider_interfaces/|packages/scene_planner/|services/local_ai/|' +
        'services/provider_router/|tests/integration/|assets/lesson-content/|' +
        'distribution/windows/|config/)' -or
        $path -match '^scripts/(package|progress|provider-credentials)\.ps1$') {
        Add-Scope 'python'
        continue
    }

    if ($path -match '\.(md|txt|png|jpg|jpeg|webp|svg)$') {
        continue
    }

    # Unknown code, build, or configuration paths are safer with the complete software gate.
    $runAll = $true
}

if ($runAll) {
    $scopes.Clear()
    Add-Scope 'all'
    $androidBuild = $false
}
elseif ($scopes.Contains('python')) {
    # The Python gate already includes contract and speech tests plus whole-tree Python mypy.
    [void] $scopes.Remove('contracts')
    [void] $scopes.Remove('speech')
}

[string[]] $orderedScopes = @(
    @('contracts', 'python', 'media', 'speech', 'kotlin', 'csharp', 'godot', 'all') |
        Where-Object { $scopes.Contains($_) }
)

if ($ListOnly) {
    Write-Output "Scopes: $($orderedScopes -join ',')"
    Write-Output "AndroidBuild: $($androidBuild.ToString().ToLowerInvariant())"
    exit 0
}

if ($orderedScopes.Count -eq 0 -and -not $androidBuild) {
    Write-Output 'Affected tests: documentation/assets only; software suites skipped.'
    exit 0
}

Push-Location $repositoryRoot
try {
    foreach ($scope in $orderedScopes) {
        Write-Output "Affected tests: running scope '$scope'."
        & (Join-Path $PSScriptRoot 'test.ps1') -Scope $scope
    }
    if ($androidBuild) {
        Write-Output "Affected tests: compiling the Android app."
        & (Join-Path $PSScriptRoot 'build.ps1') -Target android
    }
}
finally {
    Pop-Location
}

Write-Output 'Affected tests passed.'
