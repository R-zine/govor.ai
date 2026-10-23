"""Strict JSON loader for locally installed procedural environments."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import cast

from .scenes import (
    CameraPreset,
    LightingPreset,
    PrimitiveDefinition,
    PrimitiveShape,
    SceneObject,
    SceneSpecification,
    TransitionKind,
)

MAX_CUSTOM_ENVIRONMENTS = 32
MAX_ENVIRONMENT_FILE_BYTES = 262_144
ENVIRONMENT_LOCK_NAME = ".environment-import.lock"

_ROOT_FIELDS = {
    "schema_version",
    "environment_id",
    "display_name",
    "scene_id",
    "camera_preset",
    "lighting_preset",
    "transition",
    "avatar_position",
    "avatar_yaw_degrees",
    "objects",
}
_OBJECT_FIELDS = {
    "instance_id",
    "primitive",
    "size",
    "color",
    "position",
    "yaw_degrees",
    "scale",
}
_VECTOR_FIELDS = {"x", "y", "z"}


def load_environment_catalog(
    directory: str | Path,
) -> tuple[tuple[str, SceneSpecification], ...]:
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"environment directory does not exist: {root}")
    paths = sorted(path for path in root.glob("*.json") if path.is_file())
    if len(paths) > MAX_CUSTOM_ENVIRONMENTS:
        raise ValueError("environment directory contains more than 32 custom environments")

    catalog: list[tuple[str, SceneSpecification]] = []
    environment_ids: set[str] = set()
    scene_ids: set[str] = set()
    for path in paths:
        if path.stat().st_size > MAX_ENVIRONMENT_FILE_BYTES:
            raise ValueError(f"environment file exceeds 256 KiB: {path.name}")
        try:
            display_name, specification = environment_definition_from_mapping(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid environment file {path.name}: {error}") from error
        if specification.environment_id in environment_ids:
            raise ValueError(f"duplicate environment id: {specification.environment_id}")
        if specification.scene_id in scene_ids:
            raise ValueError(f"duplicate scene id: {specification.scene_id}")
        environment_ids.add(specification.environment_id)
        scene_ids.add(specification.scene_id)
        catalog.append((display_name, specification))
    return tuple(catalog)


def environment_definition_from_mapping(value: object) -> tuple[str, SceneSpecification]:
    root = _object(value, "environment", _ROOT_FIELDS)
    if _integer(root["schema_version"], "schema_version") != 1:
        raise ValueError("unsupported environment schema version")
    objects_value = root["objects"]
    if not isinstance(objects_value, list) or not 1 <= len(objects_value) <= 64:
        raise ValueError("objects must contain between one and 64 entries")
    objects: list[SceneObject] = []
    for raw_object in objects_value:
        item = _object(raw_object, "scene object", _OBJECT_FIELDS)
        shape = _choice(item["primitive"], "primitive", {"box", "cylinder", "sphere"})
        objects.append(
            SceneObject(
                instance_id=_slug(item["instance_id"], "instance_id", minimum=2),
                asset_id=None,
                position=_vector(item["position"], "position", -20.0, 20.0),
                yaw_degrees=_number(item["yaw_degrees"], "yaw_degrees", -360.0, 360.0),
                scale=_number(item["scale"], "scale", 0.1, 5.0),
                primitive=PrimitiveDefinition(
                    shape=cast(PrimitiveShape, shape),
                    size=_vector(item["size"], "size", 0.05, 20.0),
                    color=_color(item["color"], "color"),
                ),
            )
        )
    camera = _choice(root["camera_preset"], "camera_preset", {"counter", "conversation", "wide"})
    lighting = _choice(
        root["lighting_preset"],
        "lighting_preset",
        {"warm", "daylight", "terminal", "home"},
    )
    transition = _choice(root["transition"], "transition", {"fade", "cut"})
    display_name = _string(root["display_name"], "display_name", maximum=128)
    return (
        display_name,
        SceneSpecification(
            scene_id=_slug(root["scene_id"], "scene_id"),
            environment_id=_slug(root["environment_id"], "environment_id"),
            camera_preset=cast(CameraPreset, camera),
            lighting_preset=cast(LightingPreset, lighting),
            transition=cast(TransitionKind, transition),
            avatar_position=_vector(root["avatar_position"], "avatar_position", -20.0, 20.0),
            avatar_yaw_degrees=_number(
                root["avatar_yaw_degrees"], "avatar_yaw_degrees", -360.0, 360.0
            ),
            objects=tuple(objects),
        ),
    )


def _object(value: object, name: str, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} must be an object")
    result = cast(dict[str, object], value)
    actual = set(result)
    if actual != fields:
        raise ValueError(
            f"{name} fields do not match; "
            f"missing={sorted(fields - actual)}, extra={sorted(actual - fields)}"
        )
    return result


def _vector(
    value: object,
    name: str,
    minimum: float,
    maximum: float,
) -> tuple[float, float, float]:
    item = _object(value, name, _VECTOR_FIELDS)
    return (
        _number(item["x"], f"{name}.x", minimum, maximum),
        _number(item["y"], f"{name}.y", minimum, maximum),
        _number(item["z"], f"{name}.z", minimum, maximum),
    )


def _number(value: object, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{name} is outside the accepted range")
    return result


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _choice(value: object, name: str, choices: set[str]) -> str:
    text = _string(value, name, maximum=64)
    if text not in choices:
        raise ValueError(f"{name} is unsupported")
    return text


def _slug(value: object, name: str, *, minimum: int = 3) -> str:
    text = _string(value, name, maximum=64)
    pattern = rf"[a-z][a-z0-9-]{{{minimum - 1},63}}"
    if not re.fullmatch(pattern, text):
        raise ValueError(f"{name} must be a bounded slug")
    return text


def _color(value: object, name: str) -> str:
    text = _string(value, name, maximum=7)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        raise ValueError(f"{name} must be #RRGGBB")
    return text.upper()


def _string(value: object, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty string of at most {maximum} characters")
    return value
