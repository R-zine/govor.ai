# ADR-0021: Surface local content and update tools in the host pre-connect UI

- Status: accepted
- Date: 2026-11-02
- Scope: post-milestone host usability

## Context

Lesson generation, lesson import, environment import, and signed application patching already have
packaged Windows entry points, validation, and tests. They were discoverable only as `.cmd` files
beside the application, so a normal user could not find them from the running host. These actions
must not become LAN administration APIs, accept arbitrary command paths, or run the updater while
host files are open.

## Decision

Add a **Content & updates** native menu to Godot's opaque pre-connect screen. It exposes four
closed actions: create a lesson, import lessons, import environments, and apply an application
patch. The renderer resolves only exact package-owned command names below `GOVOR_INSTALL_ROOT`;
arbitrary paths and commands are rejected. Missing commands are disabled, which keeps source/editor
runs honest about unavailable packaged tools.

Creation and data imports use Windows shell execution for the exact installed `.cmd` entry point.
They run locally while the host stays active, preserving the existing loopback lesson creator and
live catalog/environment reload behavior. No file-picker value, content, or administrative command
crosses the LAN gateway.

Application patching uses a separate lifecycle. After explicit confirmation, Godot exits with the
closed code 42. The launcher observes renderer exit while it also accepts the existing console
Enter/Ctrl+C stop behavior, closes its kill-on-close job and all managed services, removes temporary
pairing files, and only then starts the exact installed `Apply-Govor-Patch.cmd` in a new console.
The signed updater retains every ADR-0016 verification and rollback rule.

## Consequences

- The existing host screen is the discoverable home for content and update tools; no additional
  desktop application or web administration service is introduced.
- Lesson/environment changes remain available without restart. Application patches necessarily
  stop the host before the local picker opens.
- A future packaged management action must be explicitly added to the renderer allow-list and its
  security/lifecycle behavior reviewed.

## Evidence and limits

Python tests cover the exact installed updater launch after shutdown; the full Python gate passed
304 tests. Godot's self-test covers the management command allow-list, and import/build/headless
self-test plus Windows export passed. The integrated all-scope gate also passed Python, Kotlin,
C#, media, Godot, and Android debug assembly. A bounded Windows renderer run wrote a UI proof
marker, but the resulting internal root-viewport capture was black and is not visual evidence;
menu layout still requires observation in a packaged interactive run. No actual import,
generation, or application patch was executed by the proof, and no LAN or physical-device claim
is made.
