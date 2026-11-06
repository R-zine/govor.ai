[CmdletBinding()]
param(
    [switch] $ListOnly,
    [switch] $Staged,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $ChangedFiles = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$scopes = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$pythonTests = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$affected = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$runAll = $false
$auditDependencies = $false

# Runtime dependencies, including lazy imports. A source change tests its reverse dependency
# closure; a test-only change runs its owning suite without selecting production consumers.
# Keep this table current when introducing a component or a new cross-component import.
$components = @{
    domain = @{ Root = 'packages/domain/'; Tests = 'packages/domain/tests'; Depends = @() }
    interfaces = @{ Root = 'packages/provider_interfaces/'; Tests = ''; Depends = @('domain') }
    security = @{ Root = 'packages/gateway_security/'; Tests = 'packages/gateway_security/tests'; Depends = @() }
    progress = @{ Root = 'packages/progress/'; Tests = 'packages/progress/tests'; Depends = @('domain') }
    scenes = @{ Root = 'packages/scene_planner/'; Tests = 'packages/scene_planner/tests'; Depends = @() }
    speech = @{ Root = 'services/speech/'; Tests = 'services/speech/tests'; Depends = @('interfaces') }
    local_ai = @{
        Root = 'services/local_ai/'; Tests = 'services/local_ai/tests'
        Depends = @('domain', 'interfaces', 'progress', 'speech')
    }
    router = @{
        Root = 'services/provider_router/'; Tests = 'services/provider_router/tests'
        Depends = @('interfaces', 'local_ai', 'progress', 'speech')
    }
    host = @{
        Root = 'apps/host/'; Tests = 'apps/host/tests'
        Depends = @('domain', 'interfaces', 'security', 'progress', 'scenes', 'local_ai', 'router')
    }
    launcher = @{
        Root = 'apps/launcher/'; Tests = 'apps/launcher/tests'
        Depends = @('domain', 'interfaces', 'security', 'scenes', 'local_ai')
    }
}

if ($Staged) {
    # pre-commit passes only existing files. Inspect the index as well so deletion-only commits
    # and both sides of a rename are checked. -z preserves spaces/Unicode without Git quoting.
    $indexPaths = @(& git -c "safe.directory=$repositoryRoot" -C $repositoryRoot diff --cached `
        --name-only --no-renames --diff-filter=ACDMRT -z)
    if ($LASTEXITCODE -ne 0) {
        throw 'Cannot inspect staged paths; affected checks were not run.'
    }
    $ChangedFiles = @($ChangedFiles) + @(($indexPaths -join "`n").Split([char]0) |
        Where-Object { $_.Length -gt 0 })
}

foreach ($rawPath in $ChangedFiles) {
    $path = $rawPath.Replace('\', '/').ToLowerInvariant()
    if ($path.StartsWith('./', [StringComparison]::Ordinal)) { $path = $path.Substring(2) }

    if ($path -match '\.md$' -or
        $path -match '^(docs/|licenses/|license$|copyright$|\.gitignore$|\.editorconfig$)') {
        continue
    }
    if ($path -match '^(pyproject\.toml|uv\.lock)$') {
        $auditDependencies = $true
        $runAll = $true
        continue
    }
    if ($path -match '^(\.github/workflows/|\.pre-commit-config\.yaml$|\.python-version$)' -or
        $path -match '^scripts/(common|test|build|bootstrap|pre-commit-tests|check-powershell-syntax)\.ps1$' -or
        $path -match '(^|/)(conftest\.py|pytest\.ini|tox\.ini|setup\.cfg)$' -or
        $path -match '^(packages/contracts/schemas/|tests/contracts/|tests/fixtures/contracts/)' -or
        $path -eq 'tests/integration/test_pre_commit_dispatch.py') {
        $runAll = $true
        continue
    }
    if ($path -match '^apps/android/' -or
        $path -match '^(gradle/|gradlew(\.bat)?$|settings\.gradle|build\.gradle)') {
        [void] $scopes.Add('kotlin')
        continue
    }
    if ($path -match '^apps/renderer/') {
        [void] $scopes.Add('godot')
        continue
    }
    if ($path -match '^packages/contracts/csharp/') {
        [void] $scopes.Add('csharp')
        if ($path -notmatch '/govor\.contracts\.tests/') { [void] $scopes.Add('godot') }
        continue
    }
    if ($path -match '^services/media/') {
        [void] $scopes.Add('media')
        continue
    }
    if ($path -match '^packages/contracts/python/') {
        # Python wire bindings are consumed throughout the host and by the separate media peer.
        foreach ($component in $components.Keys) { [void] $affected.Add($component) }
        [void] $pythonTests.Add('tests/contracts')
        [void] $scopes.Add('media')
        continue
    }
    if ($path -match '^(config/m8-vm\.json$|distribution/vm/|scripts/m8-vm\.ps1$)') {
        [void] $pythonTests.Add('tests/integration/test_m8_vm_fixture.py')
        continue
    }
    if ($path -match '^(distribution/windows/|config/release-|scripts/(package|create-application-patch|initialize-update-signing|initialize-release-signing)\.ps1$)') {
        [void] $pythonTests.Add('apps/launcher/tests')
        continue
    }
    if ($path -eq 'scripts/progress.ps1') {
        [void] $pythonTests.Add('apps/host/tests/test_progress_cli.py')
        continue
    }
    if ($path -eq 'scripts/provider-credentials.ps1') {
        [void] $pythonTests.Add('services/provider_router/tests/test_credentials.py')
        continue
    }
    if ($path -match '^assets/lesson-content/') {
        [void] $affected.Add('domain')
        [void] $pythonTests.Add('tests/contracts')
        continue
    }
    if ($path -match '^assets/environment-content/') {
        [void] $affected.Add('scenes')
        continue
    }
    if ($path -match '^tests/integration/test_[^/]+\.py$') {
        if (Test-Path -LiteralPath (Join-Path $repositoryRoot $path) -PathType Leaf) {
            [void] $pythonTests.Add($path)
        }
        else {
            # A removed/renamed test cannot be passed to pytest as a file. Collect the remaining
            # integration suite instead, without requesting a nonexistent test path.
            [void] $pythonTests.Add('tests/integration')
        }
        continue
    }

    $matched = $false
    foreach ($name in $components.Keys) {
        $component = $components[$name]
        if ($path.StartsWith($component.Root, [StringComparison]::Ordinal)) {
            if ($path.StartsWith($component.Root + 'tests/', [StringComparison]::Ordinal)) {
                [void] $pythonTests.Add($component.Tests)
            }
            else {
                [void] $affected.Add($name)
            }
            $matched = $true
            break
        }
    }
    if ($path -eq 'apps/host/src/govor_host/config.py') {
        # The router's factory tests also consume host Settings (no runtime import cycle).
        [void] $pythonTests.Add('services/provider_router/tests')
    }
    if (-not $matched) {
        # Unclassified executable/configuration paths fail conservatively. Do not silently skip
        # unknown assets: a packaged resource can break import, rendering, or content validation.
        $runAll = $true
    }
}

do {
    $expanded = $false
    foreach ($name in $components.Keys) {
        if ($affected.Contains($name)) { continue }
        foreach ($dependency in $components[$name].Depends) {
            if ($affected.Contains($dependency)) {
                [void] $affected.Add($name)
                $expanded = $true
                break
            }
        }
    }
} while ($expanded)

foreach ($name in $affected) {
    if ($components[$name].Tests) { [void] $pythonTests.Add($components[$name].Tests) }
}
if ($affected.Contains('host')) { [void] $pythonTests.Add('tests/integration/test_mock_lesson.py') }
if ($affected.Contains('security')) { [void] $scopes.Add('media') }
if ($pythonTests.Count -gt 0) { [void] $scopes.Add('python') }

if ($runAll) {
    $scopes.Clear()
    [void] $scopes.Add('all')
    $pythonTests.Clear()
}

[string[]] $orderedScopes = @(
    @('python', 'media', 'kotlin', 'csharp', 'godot', 'all') |
        Where-Object { $scopes.Contains($_) }
)
[string[]] $orderedTests = @(
    foreach ($test in ($pythonTests | Sort-Object)) {
        $covered = $false
        foreach ($other in $pythonTests) {
            if ($test.StartsWith($other + '/', [StringComparison]::OrdinalIgnoreCase)) {
                $covered = $true
                break
            }
        }
        if (-not $covered) { $test }
    }
)
Write-Output "Scopes: $($orderedScopes -join ',')"
Write-Output "PythonTests: $($orderedTests -join ',')"
Write-Output "DependencyAudit: $($auditDependencies.ToString().ToLowerInvariant())"
if ($ListOnly) { exit 0 }

if ($orderedScopes.Count -eq 0) {
    Write-Output 'Affected tests: documentation only or no staged changes; software suites skipped.'
    exit 0
}

Push-Location $repositoryRoot
try {
    foreach ($scope in $orderedScopes) {
        Write-Output "Affected tests: running scope '$scope'."
        $LASTEXITCODE = 0
        if ($scope -eq 'python') {
            & (Join-Path $PSScriptRoot 'test.ps1') -Scope python -PythonTestPaths $orderedTests
        }
        else {
            & (Join-Path $PSScriptRoot 'test.ps1') -Scope $scope
        }
        if (-not $? -or $LASTEXITCODE -ne 0) { throw "Affected test scope '$scope' failed." }
    }
    if ($auditDependencies) {
        # Dependency changes get an online vulnerability check; ordinary commits need no network
        # once their pinned tool environments are installed. No model/provider call is made.
        & uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit
        if ($LASTEXITCODE -ne 0) { throw 'Dependency vulnerability audit failed.' }
    }
}
finally {
    Pop-Location
}

Write-Output 'Affected tests passed.'
