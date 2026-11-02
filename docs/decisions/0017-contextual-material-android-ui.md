# ADR-0017: Use a contextual Material 3 Android interface

- Status: accepted; implementation and native-emulator flows verified
- Date: 2026-10-24
- Scope: post-Milestone 9 maintenance

## Context

The original Compose Activity placed connection, lesson selection, playback, pronunciation,
transcript, retry, and push-to-talk controls in one persistent overlay. This exposed actions before
they were useful, reduced the streamed scene area, and made the learner experience resemble a
developer control panel. Playback speed on the lesson-selection screen was the clearest symptom.

The product still needs every existing capability, large touch targets, readable subtitles, and a
native Android experience. The WebRTC renderer also has a lifecycle constraint: its
`SurfaceViewRenderer` must remain attached while the screens change because a remote video track
may arrive before or during a Compose state transition.

## Decision

Use the already pinned Jetpack Compose Material 3 library and its official Material icons for the
entire Android presentation layer. Apply one application theme and divide the Activity into three
mutually exclusive contexts derived from media/session state:

1. **Connection** shows only host, pairing, status, and connect controls.
2. **Lesson selection** shows the chosen lesson and primary start action. The catalog opens from a
   list icon, accent/review settings open from a settings icon, and disconnect is in an overflow
   menu.
3. **Active lesson** prioritizes the full-screen stream, progress, subtitles, learner transcript,
   errors/retry, and a prominent hold-to-talk control. Replay, speed, and pronunciation are compact
   icon actions; speed uses a dropdown and pronunciation uses a bottom sheet. Disconnect remains
   in the overflow menu.

All controls retain explicit accessibility descriptions or visible labels. State determines which
controls can exist; hidden controls are not merely disabled or visually obscured. A small pure
Kotlin state/visibility policy is unit tested without Android runtime dependencies.

Keep the `SurfaceViewRenderer` mounted behind all three contexts and change only the Compose
overlay. This preserves the proven WebRTC attachment and reconnect behavior while the interface
changes.

### State-lifecycle correction

The 2026-11-02 follow-up makes the transcript and error banner explicitly transient presentation
state. A learner transcript is cleared when a lesson ends and again before another lesson starts.
A recoverable error remains visible while the session is in `recoverable_error`, then clears only
after a normal host state confirms recovery. Starting/ending a lesson or disconnecting also clears
an obsolete error. This avoids hiding a real failure on button press while preventing a recovered
failure or the previous lesson's final answer from leaking into a healthy UI.

The correction shipped in matching signed release 0.1.19/code 20. Its portable Windows host passed
both entry-point doctors, and Android accepted the in-place physical-phone update from 0.1.18/code
19 and cold-launched the Activity. That verifies package/update compatibility, not the two lesson
interactions; they remain subject to direct learner retesting.

## Consequences

- Controls appear only in the context where they are meaningful, while every prior learner action
  remains reachable within one or two additional taps.
- Material 3 supplies consistent native components, typography, color roles, menus, sheets, and
  accessible touch behavior; the project does not maintain a custom widget system.
- Icon-only actions require stable content descriptions. Emulator smoke automation uses those
  descriptions instead of layout coordinates wherever possible.
- The official extended Material icon artifact increases the unoptimized debug APK, while release
  shrinking can retain only used resources. It does not add a new vendor or license family beyond
  the existing AndroidX/Compose Apache-2.0 dependency.
- An Android emulator verifies software behavior and accessibility structure only. This change does
  not replace or extend the historical physical-device acceptance record.

## Rejected

- Keeping one permanently visible control dashboard and changing only colors or spacing.
- Building a project-specific component library instead of using Material 3.
- A WebView, cross-platform UI framework, or renderer-owned control surface.
- Removing less common capabilities to obtain a simpler screen.
- Recreating the WebRTC video renderer on every navigation change.
