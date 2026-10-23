[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InstallRoot
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = [IO.Path]::GetFullPath($InstallRoot)
$python = Join-Path $resolvedRoot 'runtime\python\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Add-Type -AssemblyName System.Windows.Forms
    [Windows.Forms.MessageBox]::Show(
        'The packaged Python runtime is missing. Extract the complete govor.ai archive first.',
        'govor.ai lesson import',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    exit 2
}

Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object Windows.Forms.OpenFileDialog
$dialog.Title = 'Add lessons to govor.ai'
$dialog.Filter = 'Lesson files (*.json;*.zip)|*.json;*.zip|JSON lessons (*.json)|*.json|ZIP lesson bundles (*.zip)|*.zip'
$dialog.Multiselect = $false
$dialog.CheckFileExists = $true
$dialog.CheckPathExists = $true
if ($dialog.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) {
    exit 0
}

$sourceRoots = @(
    'apps\launcher\src',
    'packages\domain\src',
    'packages\gateway_security\src',
    'packages\scene_planner\src'
) | ForEach-Object { Join-Path (Join-Path $resolvedRoot 'app') $_ }
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = $sourceRoots -join [IO.Path]::PathSeparator
$previousErrorActionPreference = $ErrorActionPreference
try {
    # Native stderr is expected for a rejected import and must be captured for the result dialog.
    $ErrorActionPreference = 'Continue'
    $output = & $python -m govor_launcher.cli --install-root $resolvedRoot import-lessons --source $dialog.FileName 2>&1
    $exitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
    $env:PYTHONPATH = $previousPythonPath
}

$message = ($output | Out-String).Trim()
if ($exitCode -eq 0) {
    [Windows.Forms.MessageBox]::Show(
        "$message`n`nThe Android lesson list will update without restarting govor.ai.",
        'Lessons added',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
    exit 0
}

if (-not $message) {
    $message = 'The selected file could not be imported.'
}
[Windows.Forms.MessageBox]::Show(
    $message,
    'Lesson import failed',
    [Windows.Forms.MessageBoxButtons]::OK,
    [Windows.Forms.MessageBoxIcon]::Error
) | Out-Null
exit $exitCode
