# ADR-0016: Use signed transactional application patches

- Status: accepted; implementation and package boundary verified
- Date: 2026-10-23
- Scope: post-Milestone 9 maintenance

## Context

Environment and lesson bundles intentionally contain data only. They cannot deliver requested host
code, renderer, embedded-runtime, configuration, or Android changes. Replacing the complete
portable Windows directory remains safe, but is unnecessarily large for a small application
change and requires the learner to preserve imported content manually.

An application patch is executable authority even if represented as a ZIP. Accepting an unsigned
archive, trusting only payload hashes stored beside the payload, or running a script from the
archive would allow arbitrary local files to be replaced. Updating Android has a second trust
boundary: the platform must retain the application ID/signing identity and show its normal
user-controlled installation confirmation.

## Decision

Use a data-only `.govorpatch` ZIP with a version 1 JSON manifest, detached RSA-3072 PKCS#1
v1.5/SHA-256 signature, host payloads, and an optional release APK. Generate the update RSA
identity once below ignored, ACL-restricted `.secrets`; package only its public XML key at
`config/update-signing-public.xml`. This identity is separate from the private Android keystore.

Each packaged release contains `config/release.json` with its semantic version and Android
application/version/signer identity. `scripts/create-application-patch.ps1` compares two complete
packaged release directories and emits only add, replace, and delete operations. Every replacement
or deletion records the exact old byte length and SHA-256; every added or replacement payload
records its exact new length and SHA-256. The signed manifest binds the source version, target
version, operation list, and optional APK metadata/payload digest.

`Apply-Govor-Patch.cmd` invokes a stable package-owned PowerShell verifier. It refuses an active
host, wrong source version, unknown members, duplicate/case-colliding or traversal paths, size
excess, invalid signatures, mismatched payloads, and any local file that differs from the signed
old hash. It stages below `%LOCALAPPDATA%\govor.ai\updates`, checks the complete plan before
mutation, commits the release marker last, and restores already changed files if a later operation
fails. Unlisted files, including imported lessons and environments, are preserved.

The bootstrap scripts and update public key are not patchable in format version 1. Changing them
requires a full portable release. Releases created before this decision require one final full
upgrade before incremental patches can be used.

When an optional APK is present, the Windows updater verifies it as part of the signed archive and
saves it under `%LOCALAPPDATA%\govor.ai\updates\android`. The user copies/opens it on the phone and
approves Android's system dialog. Android enforces the stable application ID, monotonic version
code, and signing certificate. The patcher does not use ADB, silently install on a phone, weaken
unknown-source policy, or add a LAN update endpoint.

## Consequences

- Application and embedded-runtime changes can be delivered without replacing the full portable
  directory or touching per-user learner/security/model state.
- Imported content survives because only signed base-release paths are operated on; a collision or
  local edit stops the entire patch before mutation.
- Update-key loss prevents new incremental patches. It must be backed up privately with the Android
  signing identity and never distributed.
- Android updates still require visible platform confirmation. A staged APK is not evidence that a
  phone was updated.

## 2026-11-06 PowerShell module compatibility amendment

The installed verifier streams file bytes through .NET SHA-256 and disposes both the stream and
algorithm. It does not depend on the Get-FileHash function, which can disappear when a Windows
PowerShell subprocess inherits a PowerShell 7 Utility module path. Signature, old/new digest,
staging, and rollback requirements remain the same. Regression tests exercise successful updates,
late rollback, and tamper rejection with the native and shadowed Utility module layouts.
As with any verifier change, existing installations receive this bootstrap through a full release;
format version 1 patches cannot replace it.

## Rejected

- Unsigned ZIP overlays or unauthenticated checksum files.
- Self-extracting patches that run archive-supplied code before verification.
- Allowing a patch to rotate its verifier or trust key.
- Downloading patches or exposing an update administration endpoint over the LAN.
- Silent ADB installation or weakened Android package policy.
