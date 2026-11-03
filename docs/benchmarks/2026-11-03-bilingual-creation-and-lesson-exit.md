# Bilingual speech, recoverable creation, and lesson exit — 2026-11-03

## Implementation

The reported mixed-language failure came from applying one reply locale to the complete text.
The local router now segments Latin/Cyrillic spans before synthesis, uses Kokoro/Piper with the
selected teacher and English accent, and combines resampled actual PCM into one 24 kHz WAV.
Pronunciation ranges, word indices, and real provider timing are translated to the final
timeline; missing alignment is null. Fallback applies per language span. No dependency was added.

Phone generation previously belonged to `ControlSession.close()` and was cancelled when locking
the phone closed its socket. `LessonCreationJobs` now owns one bounded task independently of the
socket and retains at most 16 latest-device snapshots in memory. Authentication supplies the
owner ID; the correlation UUID identifies the job. Reconnect queries the latest state through
`lesson.create.status.request`; successful publication still replaces the live catalog.
`renderer.lesson_creation` shows activity/result on the host pre-lesson screen. Jobs time out
after 270 seconds and are cancelled on host shutdown. They do not resume across host restarts;
installed JSON does survive.

Android now has a **Leave lesson** toolbar arrow and overflow item. Android Back opens the same
Material confirmation. **Keep learning** dismisses it. **Leave lesson** stops local playback and
microphone transmission, clears automatic lesson resume, sends `session.cancel`, and returns to
selection after host cleanup without disconnecting media/control. Godot reset restores its
pre-lesson screen. Completed exercises stay saved.

## Machine and software

Windows development PC, process build 10.0.26200, Europe/Kiev. Installed local Kokoro v1.0,
Piper `bg_BG-dimitar-medium`, and Qwen3 4B Q4_K_M with llama.cpp b11540 were used for actual
model checks. Android UI used the API 34 Android Studio emulator, a new isolated task-owned
userdata image under `.cache/android-ui-regression`, sound disabled, and the new debug APK.
The previous release-signed emulator installation and the physical phone were not modified.

## Verification

`uv run --frozen --extra speech pytest apps/host/tests/test_app.py
apps/host/tests/test_lesson_creation_jobs.py services/speech/tests tests/contracts -q` passed
104 tests. Coverage includes real renderer-control status delivery/reconnect, job timeout,
duplicate requests, owner isolation, socket-close survival, bounded errors, live publication,
mixed-language voice routing, text/timestamp offsets, resampling, and explicit null timing.

`./scripts/test.ps1 -Scope kotlin`, `./scripts/test.ps1 -Scope godot`, and
`./scripts/build.ps1 -Target android` passed. Kotlin used its supported in-process fallback after
the managed account denied the user-profile daemon marker. Godot emitted the existing restricted
certificate-store/NuGet-advisory-index warnings and printed its required self-test marker.

The real-model check ran with
`uv run --frozen --extra speech .cache/mixed-creation-regression.py`. It synthesized
`Order означава поръчка. Say coffee please.` for all three profiles, with American English on
English spans and Bulgarian on Cyrillic spans. All outputs had word alignment and zero fallback.

| Profile | Measured synthesis | Duration | WAV bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| Elena (cold) | 4,498.0 ms | 3,726,166 µs | 178,900 | `f6ca7849f5528b7d325331fc67986375d164660c4d28f2ccc41185c9ee28585c` |
| Amira (warm) | 725.1 ms | 3,501,458 µs | 168,114 | `c3a051dfbba756cb145084ce6983bac8485b129f6581a05395c6ff383fc6bcff` |
| Daniel (warm) | 830.8 ms | 3,911,083 µs | 187,776 | `6ced2c255de73936442b4106e45a7d730150095587d4656877aaa2dbfeeab6d5` |

The same check started a bounded loopback llama.cpp process, requested a beginner hotel lesson
with omitted environment/length, closed its first control connection, reconnected, recovered the
same job ID, and received `created`. It installed five exercises into an isolated catalog in
22.62 seconds, increasing that catalog from four to five lessons. The model server was stopped
in `finally`; no test lesson entered learner content. Ignored machine-readable evidence is
`.cache/mixed-creation-regression.json`; WAV samples are `.cache/mixed-reply-<profile>.wav`.
No sample was played, so this is model/routing/timing evidence rather than subjective listening.

The emulator check ran with
`uv run --frozen --extra speech --extra media .cache/android-ui-regression/ui_check.py`.
It used deterministic delayed creation and diagnostic media, explicitly as UI/lifecycle fixtures.
It verified the creator sheet, request/progress card, sleep/wake, automatic reconnect, restored
terminal result, automatic selection of the installed fixture lesson, lesson start, Android Back
confirmation, **Keep learning**, toolbar leave confirmation, and return to selection with zero
active host lessons. Ignored result: `.cache/android-ui-regression/result.json`.

Initial UI attempts did not count as passes: the original emulator release signature rejected a
debug update; an unsupported audio-command invocation stopped the first isolated harness; the
soft keyboard intercepted connection taps, and the creator sheet required scrolling. The harness
was corrected and then completed. The emulator itself ran with audio disabled throughout.

The first integrated all-scope attempt failed three updater tests because it overlapped the
UI fixture's listener on 8765. Those tests correctly rejected a running app before attempting
updates. The fixture was stopped before the final full-suite retry; this was not a patch-verifier
regression and no protection was weakened.

The final `./scripts/test.ps1 -Scope all` passed after fixture teardown: 323 Python tests at
85.38% branch coverage plus Ruff/format/strict mypy, Kotlin/JVM, 11 C# tests, 21 real media tests,
Godot import/build/self-test, and Android debug assembly. The only Python warning was the existing
Starlette TestClient deprecation; Godot/NuGet repeated the documented environment warnings.

The frozen media/speech `pip-audit` reported no known vulnerabilities. Test media/control/model
servers, the app, and the task's emulator were stopped; ports 8765-8768 and audio were inactive.

## Limits and follow-up

Physical-phone lock/reconnect, camera/pairing, acoustics, learner judgment of mixed speech, and a
new signed release deployment are not inferred from these model and emulator checks. Existing
Milestone 9 acceptance remains historical evidence for its exact candidate. Recheck the installed
release on the phone with a bilingual guidance request, a creation followed by phone lock, and
leaving an active lesson. Keep the Windows host running while creation is in progress.
