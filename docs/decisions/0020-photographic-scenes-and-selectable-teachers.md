# ADR-0020: Photographic scenes and selectable facial teachers

- Status: accepted
- Date: 2026-10-26
- Scope: post-milestone visual and voice presentation

## Context

The procedural Milestone 6 avatar proved rendering, lip timing, scene changes, and media transport,
but its blocky face was not suitable for a language tutor where visible articulation matters. The
fully procedural built-in rooms also spent GPU and implementation effort on objects that a static
lesson camera did not need. The user should be able to choose among reasonable teacher options
instead of having one appearance selected permanently by the implementation.

Teacher appearance and speech presentation must stay coherent. The existing English engine has
multiple female and male Kokoro voices, while the installed Bulgarian Piper catalog contains only
the male Dimitar voice. Selection must remain closed and local: it must not allow an arbitrary
model path, voice name, download, or LLM-controlled renderer choice.

## Decision

Ship three closed CC0 teacher profiles: Elena and Amira are female; Daniel is male. Their GLBs are
generated from Ara 3D Gen's CC0 MakeHuman data, contain a skinned mesh and 34 facial blend shapes,
and contain no animation clips. Godot owns bounded idle/blink and speech animation. A host-side
menu on the pre-connect screen and the Android lesson-preferences sheet expose the same profile
catalog. A profile change is allowed only before a lesson and applies the corresponding model and
voice together.

Send that ID over the existing loopback renderer-control connection as the versioned
`renderer.teacher_profile_selected` envelope. The JSON Schema, Python, and C# bindings accept only
`elena`, `amira`, or `daniel`. The host keeps the current selection in thread-safe process memory;
health may expose the non-sensitive ID. It is not part of lesson content and cannot be produced by
the dialogue model. The authenticated Android control channel receives the closed catalog and
current ID inside `lesson.catalog`; `teacher.profile.select` contains only one advertised ID. The
host forwards a validated phone selection to Godot over loopback and returns the updated catalog
as confirmation. Godot persists selections received from either UI.

Resolve speech voices at synthesis time from the same selection:

| Profile | English `en-GB` | English `en-US` | Bulgarian |
| --- | --- | --- | --- |
| Elena | Kokoro `bf_emma` | Kokoro `af_heart` | Piper `bg_BG-dimitar-medium` + 3.5-semitone presentation |
| Amira | Kokoro `bf_isabella` | Kokoro `af_bella` | Piper `bg_BG-dimitar-medium` + 2.5-semitone presentation |
| Daniel | Kokoro `bm_george` | Kokoro `am_michael` | Piper `bg_BG-dimitar-medium` |

Use the installed neural Bulgarian Piper voice as the intelligible base for every profile. For the
female profiles, apply a bounded in-process phase-vocoder pitch presentation that preserves the
exact WAV frame count and therefore the model's timing offsets; Daniel receives the unmodified
voice. This is a transformed neural presentation, not a claim that Dimitar is a native female
speaker. The earlier eSpeak `bg+f3` route was barely understandable in the product-owner listening
run and is now prohibited even on provider failure: all Bulgarian failure fallback uses normal
`bg`, prioritizing comprehensibility over gender if the neural provider is unavailable. Optional
cloud-compatible speech uses independently configurable presentation voice names; those names are
not treated as a provider guarantee about speaker identity.

The 2026-11-03 mixed-reply correction routes each Latin/Cyrillic span separately. Passing an
entire explanation with English examples to Piper (or Bulgarian text to Kokoro) was the remaining
intelligibility defect. Each span keeps the selected teacher's language voice; English uses the
learner's accent even when the overall reply locale is Bulgarian. The router resamples actual PCM
to 24 kHz and concatenates it, translating exact text/word/timestamp offsets. Missing timing stays
null for the combined turn. Failure fallback applies only to the failed language span.

Replace the four built-in procedural rooms with four locally bundled CC0 photographic 2D
backdrops. Godot renders the selected 3D teacher in front of the image and keeps the 1280x720 media
surface, control contract, and scene IDs unchanged. Imported environment bundles retain ADR-0015's
strict data-only primitive format; they cannot add models, images, scripts, or arbitrary Godot
resources.

## Consequences

- The face and mouth occupy more of the frame, and users can change teacher appearance from the
  host pairing screen or phone lesson screen without rebuilding or restarting the host.
- Appearance, English accent, and voice presentation are separate concerns: accent remains the
  learner's setting, English uses profile-matched voices, and Bulgarian uses a profile-specific
  presentation of one bundled neural voice. A native female Bulgarian model remains preferable.
- Profile assets and built-in backdrops increase the packaged renderer size. Their exact source,
  license, generation inputs, and hashes are committed beside the assets.
- The selection is intentionally closed to three profiles. Adding a teacher requires reviewed
  assets, provenance, voice mappings, contract evolution, tests, and a new application build.
- Existing Milestone 9 physical acceptance remains historical evidence for the earlier visual
  candidate. This change has software/runtime evidence only until a later signed release is run on
  physical hardware; it does not rewrite that acceptance record.

## Rejected

- Keep the blocky procedural teacher: facial articulation and visual quality were inadequate.
- Let the LLM or lesson JSON choose model/resource paths: this would cross the existing resource
  security boundary.
- Download avatars or backgrounds at runtime: this would weaken offline behavior, reviewability,
  and licensing control.
- Keep gender-matched eSpeak as the normal Bulgarian route for female profiles: listening feedback
  found it barely understandable, which is a worse product failure than an explicitly documented
  temporary presentation mismatch.
- Treat cloud voice names as guaranteed gender metadata: compatible providers control the meaning
  of those names.
- Immediately bundle BgTTS-38M-V2: its native Bulgarian female samples are promising, but its
  current PyTorch/MioCodec/WavLM runtime is substantially larger than the existing ONNX/Piper
  stack, its checkpoint is pickle-based, and this project has not yet pinned, audited, packaged,
  or subjectively accepted that dependency chain.

## Evidence and limits

The Godot self-test validates all three allow-listed resources and required speech morphs. The
exported scene tour cycles Elena, Amira, Daniel, and Elena through the four backdrops, captures
distinct 1280x720 frames with an open viseme, and checks cache/video-memory revisit bounds. Python
tests cover closed selection, live host propagation, Kokoro voice switching, Bulgarian Piper
routing, gender-aware failure fallback, and dynamic cloud presentation voice selection. This is local
development-machine evidence. On 2026-11-02 the implementation was included in the matching signed
0.1.18/code-19 Windows/Android release, the portable host passed its entry-point doctors, and the
physical realme installation updated and cold-launched successfully. Pairing and lesson media were
not run, so the deployment is not yet physical-phone evidence for the new models, backdrops, or
voice mapping.

The later Android selector extension passed the versioned JSON Schema fixtures, 302 Python tests,
29 Kotlin/JVM tasks, 10 C# contract tests, and the Godot import/build/headless self-test on
2026-11-02. The real renderer-control test proves phone-to-host-to-renderer propagation, but no
new physical-device or subjective voice-quality claim is inferred from those software checks.
