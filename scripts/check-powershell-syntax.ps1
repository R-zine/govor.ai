[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $Paths = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$failed = $false

foreach ($path in $Paths) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }
    $tokens = $null
    $errors = $null
    [void] [Management.Automation.Language.Parser]::ParseFile(
        (Resolve-Path -LiteralPath $path).Path,
        [ref] $tokens,
        [ref] $errors
    )
    foreach ($parseError in $errors) {
        Write-Output "$path`:$($parseError.Extent.StartLineNumber): $($parseError.Message)"
        $failed = $true
    }
}

if ($failed) {
    exit 1
}

Write-Output 'PowerShell syntax passed.'
