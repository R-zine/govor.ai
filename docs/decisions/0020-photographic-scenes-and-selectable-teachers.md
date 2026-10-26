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
menu on the pre-connect screen persists one profile ID and applies the corresponding model before
the lesson begins.

Send that ID over the existing loopback renderer-control connection as the versioned
`renderer.teacher_profile_selected` envelope. The JSON Schema, Python, and C# bindings accept only
`elena`, `amira`, or `daniel`. The host keeps the current selection in thread-safe process memory;
health may expose the non-sensitive ID. It is not part of lesson content and cannot be produced by
the dialogue model.

Resolve speech voices at synthesis time from the same selection:

| Profile | English `en-GB` | English `en-US` | Bulgarian |
| --- | --- | --- | --- |
| Elena | Kokoro `bf_emma` | Kokoro `af_heart` | eSpeak NG `bg+f3` |
| Amira | Kokoro `bf_isabella` | Kokoro `af_bella` | eSpeak NG `bg+f3` |
| Daniel | Kokoro `bm_george` | Kokoro `am_michael` | Piper `bg_BG-dimitar-medium` |

The female Bulgarian route deliberately uses the less-natural local eSpeak female variant because
there is no bundled female Piper Bulgarian voice. It must not silently pair a female model with
Dimitar. Provider failure still uses the gender-matched eSpeak variant. Optional cloud-compatible
speech uses independently configurable presentation voice names; those names are not treated as a
provider guarantee about speaker identity.

Replace the four built-in procedural rooms with four locally bundled CC0 photographic 2D
backdrops. Godot renders the selected 3D teacher in front of the image and keeps the 1280x720 media
surface, control contract, and scene IDs unchanged. Imported environment bundles retain ADR-0015's
strict data-only primitive format; they cannot add models, images, scripts, or arbitrary Godot
resources.

## Consequences

- The face and mouth occupy more of the frame, and users can change teacher appearance before
  connecting without rebuilding or restarting the host.
- Appearance, English accent, and voice presentation are separate concerns: accent remains the
  learner's setting, while the chosen profile supplies the matching female/male voice within that
  accent.
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
- Use the male Bulgarian Piper voice for every profile: this would visibly mismatch the female
  teachers.
- Treat cloud voice names as guaranteed gender metadata: compatible providers control the meaning
  of those names.

## Evidence and limits

The Godot self-test validates all three allow-listed resources and required speech morphs. The
exported scene tour cycles Elena, Amira, Daniel, and Elena through the four backdrops, captures
distinct 1280x720 frames with an open viseme, and checks cache/video-memory revisit bounds. Python
tests cover closed selection, live host propagation, Kokoro voice switching, female Bulgarian
fallback, male Piper routing, and dynamic cloud presentation voice selection. This is local
development-machine evidence, not a new physical-phone or release-package acceptance result.
