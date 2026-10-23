# Application patch authoring

Application patches are for repository/application changes. Lesson and environment changes should
continue to use their narrower data-only importers.

## One-time signing setup

Run the normal release-signing initializer and back up all of `.secrets` privately:

```powershell
./scripts/initialize-release-signing.ps1
```

In addition to the Android keystore, this creates
`.secrets/update-signing-private.xml` and `.secrets/update-signing-public.xml`. Only the public key
is copied into Windows releases. Never send the private XML key, Android keystore, or signing
properties with a release or patch.

The first updater-capable version must be delivered as a complete Windows ZIP. Retain its extracted
package directory exactly; it is the base input for its first incremental patch.

## Build and create a patch

Build a target package with a higher semantic version and, whenever an APK will be included, a
higher Android `versionCode`:

```powershell
./scripts/package.ps1 -Version 0.1.13 -VersionCode 14 -NoArchive
./scripts/create-application-patch.ps1 `
  -BasePackagePath .cache/dist/govor.ai-0.1.12-windows-x64 `
  -TargetPackagePath .cache/dist/govor.ai-0.1.13-windows-x64 `
  -AndroidApkPath .cache/dist/govor.ai-0.1.13-android-release.apk `
  -OutputPath .cache/dist/govor.ai-0.1.12-to-0.1.13.govorpatch
```

Omit `-AndroidApkPath` for a host-only update. The creator refuses packages with different update
public keys, a private key that does not match the base release, a backwards Android version code,
links, unsafe/case-colliding paths, or a change to the protected updater bootstrap/trust key.

Send only the `.govorpatch`. The recipient selects it with the existing package's
`Apply-Govor-Patch.cmd`. Do not add a self-extracting script to the patch: the archive is deliberately
data-only until the already-installed verifier authenticates it.

## Verification boundary

Automated tests cover signing-key matching, manifest/payload tampering, protected bootstrap files,
schema rejection, and a real tiny add/replace/delete/APK transaction through Windows PowerShell.
Before distributing a real patch, additionally apply it to an exact copy of the supported base
package, start the resulting host, and install any included APK on the intended test phone. A
created/staged APK does not prove Android accepted or ran it.
