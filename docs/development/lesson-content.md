# Guided lesson content

The source catalog is `assets/lesson-content/*.json`. Release packaging copies these files to
`content/lessons` and sets `GOVOR_LESSON_DIRECTORY` to that directory. The running host watches the
selected directory and replaces its immutable catalog only after the complete changed directory
validates. Connected Android clients receive the new ordered catalog without a host restart or
phone reconnect. A lesson already in progress keeps its original definition until it ends.

Packaged users add content by double-clicking `Manage-Lessons.cmd` and choosing one `.json` or one
`.zip` containing multiple JSON lessons. Imports are additive: an existing `scenario_id` is never
overwritten. The picker copies canonical `<scenario_id>.json` files into `content/lessons`; it does
not execute or extract ZIP paths. Invalid batches leave the installed catalog unchanged and show a
failure dialog.

## Add a lesson

1. Copy the closest existing JSON lesson to a new file in `assets/lesson-content`.
2. Give it a unique, stable `scenario_id` slug and unique exercise IDs. Do not rename a shipped
   scenario casually: the ID is the key for persisted learner progress.
3. Set `title`, `description`, and `display_order`; Android obtains these values from the host.
4. Choose one existing `scene_template_id`: `cafe`, `supermarket`, `airport`, or `home`.
5. Replace every objective, vocabulary item, prompt, accepted phrase pattern, correction,
   Bulgarian explanation, example, misunderstanding, and completion condition.
6. Save the file. A development host that is already running reloads the complete valid catalog;
   otherwise the next start loads it. Run the verification commands below.

The three `prompts` for each exercise are ordered beginner, intermediate, advanced.
`accepted_patterns` is an array of alternatives; every string inside one alternative must occur
in normalized learner text for that alternative to match. This is bounded guided completion, not
general semantic or pronunciation scoring.

The normative shape is `packages/contracts/schemas/v1/lesson-definition.schema.json`. The loader
also enforces exact fields, supported schema version, at most 64 files, a 256 KiB per-file limit,
unique scenario/exercise IDs, and domain invariants. One bad file intentionally prevents host
startup. An invalid edit made while the host is running retains the previous valid catalog and
sets `/health` `lesson_catalog_status` to `reload_error` rather than partially changing the UI.

Reusing a scene template requires no renderer change. A genuinely new environment is code and
asset work: extend the closed scene planner and Godot procedural catalog, update contracts/tests,
and collect renderer evidence. Lesson JSON cannot name resource paths, URLs, scripts, or arbitrary
assets.

## Verify

```powershell
./scripts/test.ps1 -Scope contracts
./scripts/test.ps1 -Scope python
./scripts/test.ps1 -Scope kotlin
./scripts/build.ps1 -Target android
./scripts/test.ps1 -Scope all
```

For a development run, connect Android with **Connect and load lessons**, confirm the new title and
description appear, select it, and tap **Start lesson**. This UI/runtime check is separate from the
automated schema and progression tests.
