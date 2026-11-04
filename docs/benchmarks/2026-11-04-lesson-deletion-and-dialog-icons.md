# Lesson deletion and dialog icons — 2026-11-04

The leave menu entry and confirmation now share the Material navigation icon. A separate red
delete action names the active lesson and requires confirmation. The host accepts only the
current socket's active session UUID, cancels the session, removes its validated JSON definition
under the import lock, and broadcasts a replacement catalog. History is kept; the last lesson
and linked/outside-directory files are protected. ADR-0013 and ADR-0017 document the amendment.

## Software verification

| Check | Result |
| --- | --- |
| Focused domain/schema tests | 61 passed |
| Complete host tests | 36 passed |
| Kotlin core/app tests and UI compilation | Passed |
| Full Python gate | 354 passed; 85.60% branch coverage |
| Shared C# tests | 12 passed |
| Real aiortc media tests | 21 passed |
| Godot import/build/headless self-test | Passed |
| Android debug assembly | Passed |
| Frozen media/speech dependency audit | No known vulnerabilities |

Regression coverage includes noncanonical JSON filenames, other-file preservation, traversal-like
IDs, busy import locks, invalid remaining content, permission failures, last-lesson protection,
socket/session ownership, extra-path rejection, both clients' live catalog updates, restart
persistence, unchanged SQLite history, and cancellation of an in-flight provider.

Commands:

```powershell
uv run --frozen pytest packages/domain/tests/test_lesson_deletion.py tests/contracts -q
uv run --frozen pytest apps/host/tests/test_app.py -q
./scripts/test.ps1 -Scope kotlin
./scripts/test.ps1 -Scope all
uv run --frozen --extra media --extra speech pip-audit --cache-dir .cache/pip-audit-lesson-deletion
```

The suite ran on the Windows 10.0.26200 x64 development PC. No new dependencies were added.
The full log is `.cache/lesson-deletion-full-tests.log`; the focused Android log is
`.cache/lesson-deletion-kotlin.log`. Existing Starlette/Gradle deprecation, nonfatal pytest cache
permission, and unavailable NuGet advisory-index warnings were retained.

## Emulator fixture and limits

UI verification uses the Android Studio API 34 `Pixel_3a_API_34_extension_level_7_x86_64` emulator,
serial `emulator-5554`, with the existing isolated task-owned userdata under
`.cache/android-ui-regression`. The physical phone and the original release installation are
not changed. The emulator is hidden, snapshot saving and audio are disabled, and the retried
fixture uses `-gpu swiftshader_indirect -feature -Vulkan`. Animation scales are zero only in this
isolated test state.

The bounded harness is `.cache/lesson-deletion-ui.py`, invoked with:

```powershell
uv run --frozen --extra speech --extra media python .cache/lesson-deletion-ui.py
```

It runs the actual host and media gateway on loopback through emulator-only `adb reverse`, with
explicit fake lessons, diagnostic media, and copied disposable lesson files. It is UI/software
evidence only, not inference, speech, GPU, acoustic, or physical-network acceptance.

The final run passed:

- The active menu shows matching native icons for Leave/Delete/Disconnect, and the leave dialog
  shows the navigation icon. The delete dialog shows the trash icon and actual lesson title.
- Dismissing either confirmation retains the active session and definition file.
- Confirming deletion removes the copied café JSON, ends the session, and shows the new selector
  without reconnecting. Further validated fixture deletions arrange the last-lesson case.
- The last lesson's button container is disabled; a physical input tap on its label does nothing,
  leaving one definition and one active session. **Keep learning** and **Leave lesson** still work.
- Final host health reports zero active sessions. The app and test servers stop in `finally`;
  ports 8765–8768 are inactive, and the task-owned emulator was then stopped.

The machine-readable result is `.cache/lesson-deletion-ui/result.json`; final console output is
`.cache/lesson-deletion-ui-verified.log`. Screenshots and matching hierarchy XML are under
`.cache/lesson-deletion-ui`: `menu`, `leave-dialog`, `delete-dialog`, `selector-after-delete`, and
`last-lesson-protected`. The menu and both dialog icons plus the disabled action were visually
inspected from the actual screenshots. Slow automation hit the diagnostic café turn's default
step deadline in some screenshots; this run does not claim successful speech playback or a
complete teaching turn. The last-lesson screenshot shows the ordinary awaiting-learner controls.

The first run was blocked before the app's connection screen by an emulator System UI ANR; the
saved hierarchy is `.cache/lesson-deletion-ui/system-ui-anr.xml`. Software graphics recovered
startup, but the next accessibility dump timed out after lesson start. The helper was adjusted
to compressed dumps and bounded retries with animations disabled. A later run exercised the
deletion flow but failed an automation assertion: Android exports the text child as enabled even
when its containing button is disabled. The corrected check validates the container and verifies
that tapping cannot delete or end the last lesson. Failed attempts are retained as failures.

The feature commit is guarded by the installed pre-commit quality/contract/affected-test hooks;
its output is captured in `.cache/lesson-deletion-commit.log`.

The currently installed 0.1.22 host and phone remain unchanged. Deployment of this feature and
the earlier semantic-answer fix requires rebuilding the Windows host and Android release APK.
