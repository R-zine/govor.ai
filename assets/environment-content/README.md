# Local environment content

Validated custom environment JSON files imported from user-provided ZIP bundles are installed
here in development builds. Release packages copy this directory to `content/environments`.

Only the bounded procedural format in
`packages/contracts/schemas/v1/environment-definition.schema.json` is supported. Environment
bundles cannot contain Godot scenes, scripts, assemblies, textures, model files, paths, or URLs.
