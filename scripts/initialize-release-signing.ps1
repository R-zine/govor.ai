[CmdletBinding()]
param(
    [string]$KeystorePath = '.secrets/android-release.jks',
    [string]$PropertiesPath = '.secrets/android-signing.properties'
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-GovorEnvironment
$env:JAVA_HOME = Get-GovorJavaHome

$resolvedKeystore = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $KeystorePath))
$resolvedProperties = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot $PropertiesPath))
$secretRoot = Split-Path -Parent $resolvedKeystore
if ((Split-Path -Parent $resolvedProperties) -ne $secretRoot) {
    throw 'The keystore and signing properties must use the same protected directory.'
}

function Protect-GovorSigningDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $interactiveIdentity = "$($env:USERDOMAIN)\$($env:USERNAME)"
    & icacls.exe $Path '/inheritance:r' '/grant:r' "$interactiveIdentity`:(OI)(CI)F" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'The signing directory ACL could not be restricted for the interactive user.'
    }
    if ($currentIdentity -ne $interactiveIdentity) {
        & icacls.exe $Path '/grant:r' "$currentIdentity`:(OI)(CI)F" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw 'The signing directory ACL could not be granted to the current process identity.'
        }
    }
}

if ((Test-Path -LiteralPath $resolvedKeystore) -xor (Test-Path -LiteralPath $resolvedProperties)) {
    throw 'Release signing state is incomplete. Restore the missing file from the signing backup.'
}
if ((Test-Path -LiteralPath $resolvedKeystore) -and (Test-Path -LiteralPath $resolvedProperties)) {
    Protect-GovorSigningDirectory -Path $secretRoot
    Write-Output "Existing release signing identity retained: $resolvedKeystore"
    Write-Output 'Back up the entire .secrets directory securely; losing it prevents compatible updates.'
    & (Join-Path $PSScriptRoot 'initialize-update-signing.ps1')
    exit 0
}

New-Item -ItemType Directory -Force -Path $secretRoot | Out-Null
$randomBytes = New-Object byte[] 36
$randomNumberGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $randomNumberGenerator.GetBytes($randomBytes)
}
finally {
    $randomNumberGenerator.Dispose()
}
$password = [Convert]::ToBase64String($randomBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$keytool = Join-Path $env:JAVA_HOME 'bin\keytool.exe'
& $keytool @(
    '-genkeypair', '-v',
    '-keystore', $resolvedKeystore,
    '-storetype', 'JKS',
    '-storepass', $password,
    '-alias', 'govor-release',
    '-keypass', $password,
    '-keyalg', 'RSA', '-keysize', '3072',
    '-validity', '10000',
    '-dname', 'CN=govor.ai release,O=govor.ai,C=UA'
)
if ($LASTEXITCODE -ne 0) {
    throw 'keytool failed to create the release signing identity.'
}

$escapedKeystore = $resolvedKeystore.Replace('\', '\\')
$content = @(
    "storeFile=$escapedKeystore"
    "storePassword=$password"
    'keyAlias=govor-release'
    "keyPassword=$password"
) -join "`n"
$utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($resolvedProperties, "$content`n", $utf8WithoutBom)

Protect-GovorSigningDirectory -Path $secretRoot

Write-Output "Release signing identity created: $resolvedKeystore"
Write-Output "Gradle signing properties created: $resolvedProperties"
Write-Output 'Back up the entire .secrets directory securely; losing it prevents compatible updates.'
& (Join-Path $PSScriptRoot 'initialize-update-signing.ps1')
