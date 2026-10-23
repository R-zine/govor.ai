# Procedural environment content

Development recipes live in `assets/environment-content/*.json`; release imports live in
`content/environments`. The directory may be empty because café, supermarket, airport, and home
remain built into the scene planner. A running host watches the selected directory and swaps to a
complete valid planner snapshot without restarting.

Packaged users double-click `Manage-Environments.cmd` and select one `.zip`. The ZIP may contain
one to 32 JSON recipes. Imports are additive, so neither a built-in nor installed environment ID
is overwritten. Entries are read directly and never extracted as paths. Any invalid entry leaves
the installed catalog unchanged.

The normative JSON shape is
`packages/contracts/schemas/v1/environment-definition.schema.json`. Runtime validation is stricter
where JSON Schema cannot compare values: every number must be finite and a cylinder's X/Z sizes
must match. Each recipe supplies:

- unique `environment_id` and `scene_id` slugs plus a bounded display name;
- one closed camera, lighting, and transition preset;
- bounded teacher position/yaw; and
- one to 64 uniquely named box, cylinder, or sphere objects with size, `#RRGGBB` color, position,
  yaw, and scale.

Version 1 intentionally has no Godot scene/resource, code, model, texture, shader, filesystem path,
or URL field. Do not put `.tscn`, `.res`, `.pck`, `.glb`, image, script, or DLL members in a bundle;
the importer rejects every non-JSON entry. The valid test fixture at
`tests/fixtures/contracts/valid/environment-hotel-lobby.json` is a small authoring example.

After installing an environment, import or create a lesson whose `scene_template_id` is the new
environment ID. The lesson creator reloads its environment choices whenever its form opens. The
next lesson sends the validated primitive recipe to the running Godot renderer.

## Verify

```powershell
./scripts/test.ps1 -Scope contracts
./scripts/test.ps1 -Scope python
./scripts/test.ps1 -Scope csharp
./scripts/test.ps1 -Scope godot
./scripts/check-powershell-syntax.ps1 -Paths distribution/windows/Import-Environments.ps1,distribution/windows/Create-Lesson.ps1
```
