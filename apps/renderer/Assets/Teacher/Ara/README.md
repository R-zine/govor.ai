# Selectable teacher assets

`elena.glb`, `amira.glb`, and `daniel.glb` are generated from the CC0 MakeHuman character data in
[Ara 3D Gen](https://github.com/olatunde85/3d-gen) at commit
`0c3473d7d46a2badcdcd1dcfd4aeb0762eb04b20`. The exact generator inputs are under `profiles/`.
Each installed GLB contains one skinned high-detail mesh and 34 facial blend shapes, including
`jawOpen` and 14 Oculus-style speech visemes.

The build-time Ara exports included its `Idle` action so Blender could bake a relaxed rest pose.
`build_teacher_profiles.py` then removed every animation/action before writing the distributed
GLBs. This avoids shipping Ara's optional motion library; runtime movement and lip animation are
owned by `FacialTeacherAvatar.cs`.

Final artifact checksums:

- `elena.glb`: `0703ACEE2388EDCA7149DA23BED5CC36B5F3C1A64AF911120F15B8F4E6B68182`
- `amira.glb`: `E6C4D41D01A743FCCECADD31490C157310DA52AEE2DAD157E6831A4B1F184DB8`
- `daniel.glb`: `1BCDB7C2D1F549F2EEC1B1D92FC135FCC9B08E2C1A20F665D54E63B5DA7E0458`

The generated character assets are CC0 1.0; see `ASSETS_LICENSE.txt`. Ara's generator source is
MIT-licensed and is not bundled in the application.
