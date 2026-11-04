# ADR-0013: JSON lesson catalog with host-owned discovery

- Status: accepted
- Date: 2026-10-22
- Amended: 2026-10-22 (live imports); 2026-11-04 (confirmed active-lesson deletion)
- Scope: post-milestone product maintenance

## Context

The four guided lessons were Python constants and Android duplicated their IDs and titles. Adding
content therefore required code changes and a client rebuild, despite lessons already being
host-owned data. Scene selection was also keyed directly by scenario ID, preventing a new lesson
from reusing an existing safe environment.

## Decision

Store one versioned JSON object per lesson in `assets/lesson-content`. The domain loader reads the
directory once during host startup, applies file/count/field/value bounds, constructs immutable
`LessonDefinition` values, orders them by `display_order`, and rejects the complete startup on any
invalid file or duplicate scenario ID. Release packaging copies the directory to
`content/lessons`; `GOVOR_LESSON_DIRECTORY` selects the deployed location.

Add `lesson.catalog.request` and `lesson.catalog` to the version 1 control contract. After control
authentication, Android requests the bounded summary and builds its selector from the response.
`session.start` still contains a scenario ID, which the host resolves only against its current
validated catalog.

The packaged host includes `Manage-Lessons.cmd`, which opens a native Windows `.json`/`.zip` file
picker. The local launcher importer bounds and validates the complete batch and combined catalog,
rejects collisions, and additively publishes canonical `<scenario_id>.json` files under
`content/lessons`. ZIP entries are read without path extraction. A host watcher replaces the
immutable snapshot only after whole-directory validation and pushes `lesson.catalog` to connected
clients. An active lesson keeps the snapshot from `session.start`; the next lesson uses the latest
snapshot. Direct invalid edits retain the last valid runtime catalog. Network downloads are not
supported and no LAN administration endpoint is added.

Each lesson names one `scene_template_id` that must exist in the current validated scene planner.
The four built-ins remain `cafe`, `supermarket`, `airport`, and `home`; ADR-0015 defines additive
local environment bundles. Multiple lessons may reuse a template. A lesson import is rejected
unless its referenced built-in or custom environment is already installed.

Scenario IDs are persistent-data keys and should remain stable once shipped. Exercise counts are
provided by the active definition to progress restoration; incompatible edits must be reviewed as
data migrations rather than silently guessed.

## Consequences

### Confirmed active-lesson deletion (2026-11-04 amendment)

An authenticated phone may send `lesson.delete.request` with only its active session UUID after a
separate, named Android confirmation. The host resolves that session to its lesson, cancels its
work/capture/playback, resets the renderer, and removes exactly the validated definition file.
Deletion shares the import lock, validates the complete remaining catalog before unlinking,
refuses linked files, and retains at least one lesson. It immediately swaps the registry snapshot
and broadcasts the catalog, so restart/reconnect is unnecessary. SQLite history is retained.
Rejected IDs, invalid remaining content, busy locks, and filesystem errors do not remove files.
If removal fails after session teardown, the client receives a bounded error on the selector and
can start a lesson again. Another socket cannot delete the first socket's active lesson.

The physical definition is removed from the selected install's lesson directory, including when
the filename differs from its scenario ID. Neither the phone nor the model selects a filename.
Deleting a packaged default is an intentional local content change: a later fresh full package
contains its own defaults; an incremental patch that needs that missing base file fails the
existing conflict check rather than weakening signature/hash validation.

- A valid imported JSON lesson appears in connected Android clients without restarting or
  reconnecting, and requires no Python, Kotlin, or Godot changes when it reuses an existing scene
  template.
- Invalid or partially valid content never produces a partially available teaching catalog.
- Lesson content remains deterministic, local, reviewable, schema-tested, and independent of
  provider/model output.
- The Android client requires the catalog handshake before starting a new lesson.
- Four existing scenario IDs, teaching content, progress keys, and renderer scene IDs remain
  unchanged.

## Rejected

- Loading arbitrary JSON independently on Android, which would split teaching authority and
  require synchronizing files between devices.
- Silently skipping invalid lesson files, which would hide deployment mistakes.
- Mutating an active lesson to a newly loaded definition; active sessions instead retain their
  original immutable snapshot.
- A LAN-facing upload/admin endpoint, which would unnecessarily expand the authenticated attack
  surface for a same-PC file-selection operation.
- Allowing content to name paths, URLs, scripts, or arbitrary renderer assets.
