# ADR-0014: Local structured lesson creator

- Status: accepted
- Date: 2026-10-23
- Scope: post-milestone product maintenance

## Context

ADR-0013 moved lesson definitions into a validated JSON catalog and added additive local imports.
Authors still had to write the complete schema by hand. A nontechnical Windows user needs to be
able to describe a lesson, optionally choose its content difficulty, visual environment, and
length, and use the result without editing JSON or restarting the host.

Lesson generation has a different trust profile from a normal teaching turn. The model must
produce a larger object, but it must not choose installation paths, persistent identifiers,
catalog order, renderer assets, or application actions. A failed generation must not leave a
partial or invalid catalog.

## Decision

Package `Create-Lesson.cmd` with a native Windows form and expose the same operation beside the
Android lesson selector after the phone has authenticated. The topic is required. Difficulty,
environment, and exercise count are optional; deterministic application code resolves omissions
to intermediate difficulty, five exercises, and an allow-listed scene selected from topic
keywords or a stable topic hash. ADR-0015 makes the allow-list include validated installed
environments, and the form obtains current display names from the launcher. Supported explicit
lengths are one through eight exercises.

The creator sends one bounded structured request to the existing loopback-only llama.cpp server.
The response must match the versioned `local-ai-lesson-content` schema and is independently parsed
with unknown fields forbidden. Content difficulty guides the generated vocabulary and situations;
the resulting lesson still includes beginner/intermediate/advanced prompts so the existing
adaptive teaching engine remains authoritative.

Application code creates unique slug IDs, display order, exercise IDs, schema version, and the
validated scene-template field. It then validates the complete `lesson-definition` and publishes it
through the same locked additive importer introduced by ADR-0013. The host's existing catalog
watcher sends the replacement summary to connected Android clients. An active lesson is unchanged.

No new HTTP endpoint is added. Android uses the existing certificate-pinned, device-authenticated
control WebSocket with strict `lesson.create.request` and `lesson.create.result` envelopes. The
operation is pre-lesson only, permits one in-flight phone generation per host, and carries no
path, model name, command, or file. The host resolves the current validated environment catalog,
runs the same creator against loopback llama.cpp, atomically publishes through the importer, and
broadcasts a replacement catalog. The local Windows form remains available.

The creator has no cloud fallback. `Start-Govor.cmd` must be running because it owns the packaged
llama.cpp process. The topic and generated content are not logged by the creator.

### Phone lifecycle correction

The host, rather than a control socket, owns the phone creation task. Its latest bounded snapshot
is keyed by the authenticated device identity, with the request correlation UUID as job identity.
Closing the phone socket does not cancel the job. `lesson.create.status.request` restores
`idle`, `generating`, `created`, or `failed` plus an actual terminal result after reconnect.
One global task and at most 16 latest-device snapshots are retained in memory; the overall job
deadline is 270 seconds. Duplicate requests for the active job return its existing status.
Shutdown cancels unfinished work; installed lesson JSON survives, but unfinished jobs do not
resume after host restart. Topics and partial model output are not persisted as job history.

The host pushes `renderer.lesson_creation` over loopback so the pre-lesson screen shows an
indeterminate progress bar and final result. Renderer/socket loss does not fail generation.
Android requests its own status after every catalog load/reconnect, and automatically selects
the published lesson. Pre-lesson failures remain separate from session-recovery errors.

## Consequences

- A generated lesson is a normal human-readable JSON file under `content/lessons` and survives
  host restarts.
- Connected Android clients receive it without restarting or reconnecting, and the requesting
  phone selects the new lesson when the refreshed catalog arrives.
- Malformed model output, unsupported scenes, catalog collisions at publication time, and invalid
  lesson definitions fail before installation.
- Model quality still affects pedagogical quality. Structural validation does not imply that every
  generated lesson is factually or pedagogically ideal.
- Release phone creation is available only after normal pairing/device authentication. Debug mode
  retains its explicitly insecure development boundary and is not release evidence.

## Rejected

- Letting the model emit a complete installable lesson, because that would allow it to select
  paths, IDs, ordering, and scene identifiers.
- Adding a separate LAN lesson-generation HTTP endpoint. Reusing the authenticated bounded control
  channel avoids another listener/authentication surface while making the function discoverable.
- Generating omitted settings in a second model call. Deterministic defaults are faster,
  repeatable, and sufficient.
- Mutating an existing lesson. Generated content remains additive so persisted progress keys are
  never silently redefined.
