# ADR-0015: Patchable procedural environment bundles

- Status: accepted
- Date: 2026-10-23
- Scope: post-milestone product maintenance

## Context

The original Godot renderer included four safe procedural environments in code. Adding a hotel,
restaurant, or other visual setting required rebuilding the host and renderer, while lesson JSON
was already locally patchable. Users need to install a supplied environment pack and use it in new
or imported lessons without restarting the host. Accepting arbitrary Godot resources or 3D files
would turn an untrusted ZIP into executable/resource-loading authority and add unresolved format,
licensing, and dependency risks.

## Decision

Define a version 1 environment bundle as a ZIP containing one to 32 JSON files. Each file is an
exact, versioned recipe with a unique bounded environment/scene ID, display name, closed
camera/lighting/transition presets, bounded teacher placement, and one to 64 objects. Each object
is exactly one colored `box`, `cylinder`, or `sphere` with bounded size and transform. The format
has no path, URL, script, Godot node/resource name, material shader, texture, model, or assembly
field.

Package `Manage-Environments.cmd` and a native ZIP picker. The launcher reads entries directly
without extracting paths, rejects encrypted/non-JSON/unsafe/oversized input and built-in or
installed ID collisions, validates the complete resulting catalog, then additively publishes
canonical `<environment_id>.json` files under `content/environments` using a local import lock.
Partial failure removes every staged file.

The host maintains an immutable `ScenePlanner` snapshot. It polls the environment directory,
replaces the snapshot only when every environment and current lesson reference validates, and
reports `environment_catalog_status`. New sessions request the current planner; an active scene is
not mutated. The lesson importer and creator resolve their allowed environments from the same
installed directory, and the creator form lists their display names dynamically.

The renderer contract represents an object as exactly one built-in asset ID or one validated
primitive. Godot constructs custom primitives in memory with its existing cached meshes and
materials. No Godot project patch or renderer restart is needed.

## Consequences

- Environment packs are local, additive, offline, human-readable, and usable by later lessons
  without rebuilding either client or restarting the host.
- Version 1 intentionally cannot ship authored meshes, textures, animations, collision logic, or
  scripts. A richer format requires a separately reviewed contract and licensing/security design.
- Removing or editing installed files out of band is unsupported for active content; invalid
  edits retain the last valid runtime snapshot.
- The existing four built-ins, scene IDs, renderer smoke tour, and prior physical acceptance
  evidence remain unchanged.

## Rejected

- Shipping `.tscn`, `.res`, `.pck`, DLL, GDScript, or C# files in user bundles.
- Loading `.glb`, textures, shaders, filesystem paths, or URLs directly from a bundle.
- Extracting the ZIP into the Godot project or replacing application files.
- Exposing a LAN upload or environment-management endpoint.
- Restarting all services after every valid import when an immutable planner swap is sufficient.
