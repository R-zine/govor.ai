"""Bake one Ara export to a relaxed static pose and remove bundled animation clips.

Run with Blender 5.1 or newer:
  blender --background --python build_teacher_profiles.py -- SOURCE.glb DESTINATION.glb
"""

import sys
from pathlib import Path

import bpy


def build(source: Path, destination: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    idle = bpy.data.actions.get("Idle")
    if len(armatures) != 1 or idle is None:
        raise RuntimeError("Expected one armature and the Ara Idle build-time action")

    armature = armatures[0]
    armature.animation_data_create()
    armature.animation_data.action = idle
    bpy.context.scene.frame_set(20)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    for item in bpy.context.scene.objects:
        item.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)

    destination.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(destination),
        export_format="GLB",
        export_animations=False,
        export_skins=True,
        export_morph=True,
        export_morph_normal=False,
        export_morph_tangent=False,
        export_yup=True,
    )


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise SystemExit("Expected SOURCE and DESTINATION after --")
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 2:
        raise SystemExit("Usage: build_teacher_profiles.py SOURCE DESTINATION")
    build(*(Path(value).resolve() for value in arguments))
