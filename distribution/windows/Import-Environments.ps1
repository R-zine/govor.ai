[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InstallRoot
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = [IO.Path]::GetFullPath($InstallRoot)
$python = Join-Path $resolvedRoot 'runtime\python\python.exe'
Add-Type -AssemblyName System.Windows.Forms
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    [Windows.Forms.MessageBox]::Show(
        'The packaged Python runtime is missing. Extract the complete govor.ai archive first.',
        'govor.ai environment import',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 2
}

$dialog = New-Object Windows.Forms.OpenFileDialog
$dialog.Title = 'Add 3D environments to govor.ai'
$dialog.Filter = 'Environment bundles (*.zip)|*.zip'
$dialog.Multiselect = $false
$dialog.CheckFileExists = $true
$dialog.CheckPathExists = $true
if ($dialog.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { exit 0 }

$sourceRoots = @(
    'apps\launcher\src',
    'packages\gateway_security\src',
    'packages\scene_planner\src'
) | ForEach-Object { Join-Path (Join-Path $resolvedRoot 'app') $_ }
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $sourceRoots -join [IO.Path]::PathSeparator
$previousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $output = & $python -m govor_launcher.cli --install-root $resolvedRoot import-environments --source $dialog.FileName 2>&1
    $exitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
    $env:PYTHONPATH = $previousPythonPath
}

$message = ($output | Out-String).Trim()
if ($exitCode -eq 0) {
    [Windows.Forms.MessageBox]::Show(
        "$message`n`nNew lessons can use the environment immediately.",
        'Environment added',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
    exit 0
}
if (-not $message) { $message = 'The selected environment bundle could not be imported.' }
[Windows.Forms.MessageBox]::Show(
    $message,
    'Environment import failed',
    [Windows.Forms.MessageBoxButtons]::OK,
    [Windows.Forms.MessageBoxIcon]::Error
) | Out-Null
exit $exitCode
