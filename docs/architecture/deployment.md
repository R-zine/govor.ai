# Deployment architecture

Development uses repository-local Python, Gradle, NuGet, .NET, and Godot caches. The Android app
is built with its Gradle wrapper; the host runs through `uv`. The pinned Godot .NET editor and
export templates are installed into ignored repository-local tooling by
`scripts/bootstrap.ps1 -IncludeRenderer`.

The eventual Windows distribution will include a launcher, embedded Python host, renderer/media
process, local providers, configuration, and lesson assets. Models remain separately downloaded
with pinned identifiers and verified checksums. The Android release uses the stable application ID
`ai.govor.app` and a user-controlled signing key that is never committed.

Normal operation is one Windows host and one paired Android client on the same LAN, without
internet, PC speakers, PC microphone, active monitor, or developer tooling. That deployment is a
target, not a currently verified capability.
