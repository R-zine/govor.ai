# ADR-0008: Deterministic guided teaching with structured SQLite progress

- Status: accepted
- Date: 2026-10-12
- Milestone: 5

ADR-0013 amends only the storage and discovery mechanism: definitions are now strict external
JSON loaded into the same framework-independent domain model, and Android discovers the catalog
from the host. The deterministic teaching and persistence decisions below remain in force.

## Context

The bilingual dialogue model can produce natural wording, but it is not a reliable authority for
lesson completion, correction policy, or learner difficulty. Milestone 5 also requires interrupted
lesson resume, explainable adaptation, vocabulary/comprehension history, learner settings, and
deletion/export without retaining microphone recordings or complete transcripts.

Four guided scenarios must work before Milestone 6 scene work begins: café, supermarket, airport,
and home. Their goals and valid learner outcomes need to remain testable when the local model is
unavailable or changes in a later release.

## Decision

Keep lesson definitions and progression in framework-independent `packages/domain`. Each scenario
defines objectives, vocabulary, examples, three difficulty prompts, exercise types, expected
learner intents, accepted phrase patterns, common misunderstandings, gentle corrections,
Bulgarian explanations, and a completion condition. Matching is deliberately bounded and
deterministic; it is suitable for these guided exercises and is not presented as general language
or pronunciation scoring.

Patterns may contain one bounded named slot after a literal phrase when the prompt deliberately
allows a learner-chosen value. For example, `flying to` plus `{destination}` accepts London, New
York, or another supplied destination while still rejecting `flying to` without a value and
`flying from`. Slots do not delegate scoring to the dialogue model; the domain matcher remains the
sole deterministic progression authority.

The dialogue provider remains advisory. It receives the active exercise context and may classify
the learner intent, but `TeachingEngine` alone decides whether the turn is a help request, failed
attempt, successful English production, exercise advance, or lesson completion. Bulgarian and
mixed-language assistance never count as successful English production. Help and no-speech turns
retain the active exercise. The engine supplies the final gentle correction or next prompt so a
model cannot award progress or skip content.

Difficulty starts at the persisted learner setting. Two unsuccessful English attempts reduce it
one level; two consecutive first-attempt successes raise it one level. The resulting reason is a
closed enum and travels with progress, making every change visible and testable. Beginner support
adds the committed Bulgarian explanation without silently inventing success.

Store progress through `packages/progress` in SQLite. The development default is
`data/progress.sqlite3`, which is ignored by Git. The schema stores only:

- learner accent, starting difficulty, and spaced-review preference;
- current scenario/exercise, counters, completion count, and active/resume state;
- per-exercise attempts, successes, and help-request counts;
- per-vocabulary attempts, successes, and bounded review date;
- difficulty changes and their closed reasons.

It does not accept or store transcript text or audio. Each evaluated turn is one SQLite
transaction. A completed scenario becomes inactive; selecting it again starts a new attempt while
preserving history. An interrupted active scenario resumes at the saved exercise. The optional
spaced-review query is disabled unless the learner enables it.

Android selects one of the four scenario IDs plus `en-GB`/`en-US` and the review preference in the
version 1 `session.start` payload. Every `teacher.turn` includes a validated `lesson_progress`
snapshot. The host ends a completed session only after Android reports that the final teacher audio
finished. `scripts/progress.ps1` provides local view, JSON export, and confirmation-gated history
deletion; deletion preserves explicit learner settings.

The host also projects a bounded summary into every `lesson.catalog` item: `not_started`,
`in_progress`, or `completed`, successful versus total exercises, and the historical completion
count. This projection is read from the same SQLite authority and contains no transcript, audio, or
per-exercise history. Android requests a fresh catalog after every session boundary and shows the
summary both on the selected lesson card and in the lesson picker; it does not invent or persist a
second progress source.

## Security and privacy consequences

- The database has no network listener and remains owned by the trusted Windows user.
- Normal logs still omit full transcripts and audio; the database schema has no columns for either.
- Scenario IDs are resolved through the committed allow-list before a session starts.
- Export contains the same structured counters and settings, never hidden audio/transcript fields.
- Deletion is explicit and confirmation-gated in the CLI.
- Release packaging must move the database to an appropriate per-user application-data directory
  and preserve it across upgrades; the repository-local development path is not the final installer
  location.

## Rejected

- Trusting the model's `advance_exercise` flag: model sampling or malformed output could award
  progress inconsistently.
- Persisting conversation memory or complete transcripts: neither is needed for progression and it
  would increase privacy risk.
- Treating recognition success as exercise success: the recognized words must satisfy the active
  guided goal, and Bulgarian assistance remains non-advancing.
- Adding a general proficiency or pronunciation score from these phrase patterns: the current
  evidence supports guided completion only.
- Hard-coding progress solely in Android: the Windows host owns teaching policy and must resume
  consistently across client/process restarts.

## Evidence and limits

Pure-domain tests cover all four definitions, help invariants, Bulgarian non-advancement,
correction, difficulty decrease/increase, and complete lesson progression. SQLite tests close and
reopen the database, resume the next exercise, record vocabulary/help/adaptation, schedule optional
review, export structured JSON, delete history, and prove a sentinel transcript is absent.

Host tests cover scenario selection, catalog progress projection, progress delivery, and completion
only after final playback.
The local lesson integration completes a café lesson through recognition/dialogue/speech-shaped
boundaries and restarts against the same SQLite file. Kotlin and C# decode the shared progress
fixture, and the Android debug application compiles with scenario/settings controls and progress
display.

These tests do not establish broad pedagogical efficacy, recognition accuracy, live-human lesson
quality, or target-hardware usability. Those require ongoing content evaluation; the physical
phone, Wi-Fi, acoustics, performance, and bounded-stability acceptance was later executed and
passed separately in Milestone 9.
