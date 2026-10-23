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

Package `Create-Lesson.cmd` with a native Windows form. The topic is required. Difficulty,
environment, and exercise count are optional; deterministic application code resolves omissions
to intermediate difficulty, five exercises, and an allow-listed scene selected from topic
keywords or a stable topic hash. Supported explicit lengths are one through eight exercises.

The creator sends one bounded structured request to the existing loopback-only llama.cpp server.
The response must match the versioned `local-ai-lesson-content` schema and is independently parsed
with unknown fields forbidden. Content difficulty guides the generated vocabulary and situations;
the resulting lesson still includes beginner/intermediate/advanced prompts so the existing
adaptive teaching engine remains authoritative.

Application code creates unique slug IDs, display order, exercise IDs, schema version, and the
closed scene-template field. It then validates the complete `lesson-definition` and publishes it
through the same locked additive importer introduced by ADR-0013. The host's existing catalog
watcher sends the replacement summary to connected Android clients. An active lesson is unchanged.

The creator has no LAN endpoint and no cloud fallback. `Start-Govor.cmd` must be running because it
owns the packaged llama.cpp process. The topic and generated content are not logged by the creator.

## Consequences

- A generated lesson is a normal human-readable JSON file under `content/lessons` and survives
  host restarts.
- Connected Android clients receive it without restarting or reconnecting.
- Malformed model output, unsupported scenes, catalog collisions at publication time, and invalid
  lesson definitions fail before installation.
- Model quality still affects pedagogical quality. Structural validation does not imply that every
  generated lesson is factually or pedagogically ideal.
- The current creator is local-release UI; it does not expose lesson administration to the phone
  or network.

## Rejected

- Letting the model emit a complete installable lesson, because that would allow it to select
  paths, IDs, ordering, and scene identifiers.
- Adding a LAN lesson-generation endpoint, which would expand authentication, authorization, and
  abuse-prevention scope for a same-PC operation.
- Generating omitted settings in a second model call. Deterministic defaults are faster,
  repeatable, and sufficient.
- Mutating an existing lesson. Generated content remains additive so persisted progress keys are
  never silently redefined.
