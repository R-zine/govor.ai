"""Allow-listed in-memory scene recipes.

The planner emits only deterministic identifiers and bounded transforms. It never accepts a file
path, URL, script, or model-authored asset reference.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal

EnvironmentId = str
CameraPreset = Literal["counter", "conversation", "wide"]
LightingPreset = Literal["warm", "daylight", "terminal", "home"]
TransitionKind = Literal["fade", "cut"]
PrimitiveShape = Literal["box", "cylinder", "sphere"]

ALLOWED_ASSET_IDS: Final[frozenset[str]] = frozenset(
    {
        "airport-bench",
        "airport-counter",
        "airport-sign",
        "airport-suitcase",
        "cafe-chair",
        "cafe-counter",
        "cafe-cup",
        "cafe-table",
        "home-bookshelf",
        "home-lamp",
        "home-sofa",
        "home-table",
        "market-basket",
        "market-crate",
        "market-shelf",
    }
)


@dataclass(frozen=True, slots=True)
class PrimitiveDefinition:
    shape: PrimitiveShape
    size: tuple[float, float, float]
    color: str

    def __post_init__(self) -> None:
        if self.shape not in {"box", "cylinder", "sphere"}:
            raise ValueError("scene primitive shape is unsupported")
        if any(not 0.05 <= component <= 20.0 for component in self.size):
            raise ValueError("scene primitive size is outside the accepted range")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.color):
            raise ValueError("scene primitive color must be #RRGGBB")
        if self.shape == "cylinder" and not math.isclose(
            self.size[0], self.size[2], rel_tol=0.0, abs_tol=0.001
        ):
            raise ValueError("cylinder x and z size must match")


@dataclass(frozen=True, slots=True)
class SceneObject:
    instance_id: str
    asset_id: str | None
    position: tuple[float, float, float]
    yaw_degrees: float = 0.0
    scale: float = 1.0
    primitive: PrimitiveDefinition | None = None

    def __post_init__(self) -> None:
        if not self.instance_id or len(self.instance_id) > 64:
            raise ValueError("scene object instance_id is invalid")
        if (self.asset_id is None) == (self.primitive is None):
            raise ValueError("scene object requires exactly one asset or primitive")
        if self.asset_id is not None and self.asset_id not in ALLOWED_ASSET_IDS:
            raise ValueError("scene object asset_id is not allow-listed")
        if any(not -20.0 <= component <= 20.0 for component in self.position):
            raise ValueError("scene object position is outside the accepted range")
        if not -360.0 <= self.yaw_degrees <= 360.0:
            raise ValueError("scene object yaw is outside the accepted range")
        if not 0.1 <= self.scale <= 5.0:
            raise ValueError("scene object scale is outside the accepted range")


@dataclass(frozen=True, slots=True)
class SceneSpecification:
    scene_id: str
    environment_id: EnvironmentId
    camera_preset: CameraPreset
    lighting_preset: LightingPreset
    transition: TransitionKind
    avatar_position: tuple[float, float, float]
    avatar_yaw_degrees: float
    objects: tuple[SceneObject, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", self.scene_id):
            raise ValueError("scene_id is invalid")
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", self.environment_id):
            raise ValueError("environment_id is invalid")
        if any(not -20.0 <= component <= 20.0 for component in self.avatar_position):
            raise ValueError("avatar position is outside the accepted range")
        if not -360.0 <= self.avatar_yaw_degrees <= 360.0:
            raise ValueError("avatar yaw is outside the accepted range")
        if not 1 <= len(self.objects) <= 64:
            raise ValueError("scene must contain between one and 64 objects")
        instance_ids = [item.instance_id for item in self.objects]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("scene object instance IDs must be unique")


_SCENE_TEMPLATES: Final[MappingProxyType[str, SceneSpecification]] = MappingProxyType(
    {
        "cafe": SceneSpecification(
            scene_id="cafe-ordering-v1",
            environment_id="cafe",
            camera_preset="counter",
            lighting_preset="warm",
            transition="fade",
            avatar_position=(0.0, 0.0, -0.55),
            avatar_yaw_degrees=0.0,
            objects=(
                SceneObject("counter", "cafe-counter", (0.0, 0.0, 0.75)),
                SceneObject("table-left", "cafe-table", (-3.0, 0.0, 0.3), 12.0),
                SceneObject("chair-left", "cafe-chair", (-3.0, 0.0, 1.35), 180.0),
                SceneObject("cup", "cafe-cup", (0.65, 1.05, 0.55), 0.0, 0.9),
            ),
        ),
        "supermarket": SceneSpecification(
            scene_id="supermarket-shopping-v1",
            environment_id="supermarket",
            camera_preset="wide",
            lighting_preset="daylight",
            transition="fade",
            avatar_position=(0.0, 0.0, -0.45),
            avatar_yaw_degrees=0.0,
            objects=(
                SceneObject("shelf-left", "market-shelf", (-3.4, 0.0, -0.6), 8.0),
                SceneObject("shelf-right", "market-shelf", (3.4, 0.0, -0.6), -8.0),
                SceneObject("basket", "market-basket", (-1.0, 0.0, 1.2), 12.0),
                SceneObject("crate", "market-crate", (1.65, 0.0, 1.0), -10.0),
            ),
        ),
        "airport": SceneSpecification(
            scene_id="airport-travel-v1",
            environment_id="airport",
            camera_preset="counter",
            lighting_preset="terminal",
            transition="fade",
            avatar_position=(0.0, 0.0, -0.6),
            avatar_yaw_degrees=0.0,
            objects=(
                SceneObject("check-in", "airport-counter", (0.0, 0.0, 0.85)),
                SceneObject("departures", "airport-sign", (-2.6, 2.2, -1.3), 0.0, 0.9),
                SceneObject("bench", "airport-bench", (3.1, 0.0, 0.2), -12.0),
                SceneObject("suitcase", "airport-suitcase", (-1.55, 0.0, 1.3), 10.0),
            ),
        ),
        "home": SceneSpecification(
            scene_id="home-conversation-v1",
            environment_id="home",
            camera_preset="conversation",
            lighting_preset="home",
            transition="fade",
            avatar_position=(0.0, 0.0, -0.5),
            avatar_yaw_degrees=0.0,
            objects=(
                SceneObject("sofa", "home-sofa", (-2.8, 0.0, -0.65), 8.0),
                SceneObject("coffee-table", "home-table", (-1.35, 0.0, 1.0), 4.0),
                SceneObject("lamp", "home-lamp", (3.3, 0.0, -0.8), 0.0),
                SceneObject("books", "home-bookshelf", (3.5, 0.0, -1.2), -4.0),
            ),
        ),
    }
)


class ScenePlanner:
    """Resolve lesson context to a built-in or validated local environment recipe."""

    def __init__(self, environment_directory: str | Path | None = None) -> None:
        templates = dict(_SCENE_TEMPLATES)
        display_names = {
            "cafe": "Café",
            "supermarket": "Supermarket",
            "airport": "Airport",
            "home": "Home",
        }
        if environment_directory is not None:
            from .environment_catalog import load_environment_catalog

            for display_name, specification in load_environment_catalog(environment_directory):
                if specification.environment_id in templates:
                    raise ValueError(f"environment already exists: {specification.environment_id}")
                templates[specification.environment_id] = specification
                display_names[specification.environment_id] = display_name
        self._templates = MappingProxyType(templates)
        self._display_names = MappingProxyType(display_names)

    @property
    def supported_templates(self) -> tuple[str, ...]:
        return tuple(self._templates)

    @property
    def environment_choices(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (environment_id, self._display_names[environment_id])
            for environment_id in self._templates
        )

    def plan(self, scene_template_id: str) -> SceneSpecification:
        try:
            return self._templates[scene_template_id]
        except KeyError as error:
            raise ValueError("scene_template_id is not allow-listed") from error
