[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $BasePackagePath,
    [Parameter(Mandatory = $true)] [string] $TargetPackagePath,
    [Parameter(Mandatory = $true)] [string] $OutputPath,
    [string] $PrivateKeyPath = '.secrets/update-signing-private.xml',
    [string] $AndroidApkPath = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$resolvedBase = [IO.Path]::GetFullPath($BasePackagePath)
$resolvedTarget = [IO.Path]::GetFullPath($TargetPackagePath)
$resolvedOutput = [IO.Path]::GetFullPath($OutputPath)
$resolvedPrivateKey = if ([IO.Path]::IsPathRooted($PrivateKeyPath)) {
    [IO.Path]::GetFullPath($PrivateKeyPath)
}
else { [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $PrivateKeyPath)) }
if (-not (Test-Path -LiteralPath $resolvedPrivateKey -PathType Leaf)) {
    throw 'Application update signing is not initialized. Run ./scripts/initialize-update-signing.ps1 first.'
}

$pythonPath = Join-Path $script:RepositoryRoot 'apps\launcher\src'
$oldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($oldPythonPath) {
    $pythonPath + [IO.Path]::PathSeparator + $oldPythonPath
}
else { $pythonPath }
try {
    $arguments = @(
        'run', '--frozen', 'python', '-m', 'govor_launcher.application_patch', 'create',
        '--base', $resolvedBase,
        '--target', $resolvedTarget,
        '--output', $resolvedOutput,
        '--private-key', $resolvedPrivateKey
    )
    if ($AndroidApkPath) {
        $arguments += @('--android-apk', [IO.Path]::GetFullPath($AndroidApkPath))
    }
    Invoke-Checked -FilePath 'uv' -ArgumentList $arguments
}
finally { $env:PYTHONPATH = $oldPythonPath }
