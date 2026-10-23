[CmdletBinding()]
param(
    [string] $PrivateKeyPath = '.secrets/update-signing-private.xml',
    [string] $PublicKeyPath = '.secrets/update-signing-public.xml'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment

$resolvedPrivateKey = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $PrivateKeyPath))
$resolvedPublicKey = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $PublicKeyPath))
$secretRoot = Split-Path -Parent $resolvedPrivateKey
if ((Split-Path -Parent $resolvedPublicKey) -ne $secretRoot) {
    throw 'The private and public update keys must use the same protected directory.'
}

function Protect-GovorUpdateSigningDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $interactiveIdentity = "$($env:USERDOMAIN)\$($env:USERNAME)"
    & icacls.exe $Path '/inheritance:r' '/grant:r' "$interactiveIdentity`:(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'The update signing directory ACL could not be restricted for the interactive user.'
    }
    if ($currentIdentity -ne $interactiveIdentity) {
        & icacls.exe $Path '/grant:r' "$currentIdentity`:(OI)(CI)F" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw 'The update signing directory ACL could not be granted to the current process identity.'
        }
    }
}

if ((Test-Path -LiteralPath $resolvedPrivateKey) -xor (Test-Path -LiteralPath $resolvedPublicKey)) {
    throw 'Application update signing state is incomplete. Restore the missing key from backup.'
}
if ((Test-Path -LiteralPath $resolvedPrivateKey) -and (Test-Path -LiteralPath $resolvedPublicKey)) {
    Protect-GovorUpdateSigningDirectory -Path $secretRoot
    Write-Output "Existing application update signing identity retained: $resolvedPrivateKey"
    Write-Output 'Back up the private update key securely; losing it prevents trusted incremental updates.'
    exit 0
}

New-Item -ItemType Directory -Force -Path $secretRoot | Out-Null
$rsa = [Security.Cryptography.RSACryptoServiceProvider]::new(3072)
$rsa.PersistKeyInCsp = $false
try {
    $privateXml = $rsa.ToXmlString($true)
    $publicXml = $rsa.ToXmlString($false)
}
finally { $rsa.Dispose() }

$utf8WithoutBom = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText($resolvedPrivateKey, "$privateXml`n", $utf8WithoutBom)
[IO.File]::WriteAllText($resolvedPublicKey, "$publicXml`n", $utf8WithoutBom)
Protect-GovorUpdateSigningDirectory -Path $secretRoot

Write-Output "Application update private key created: $resolvedPrivateKey"
Write-Output "Application update public key created: $resolvedPublicKey"
Write-Output 'Back up the private update key securely. It is never included in a release or patch.'
