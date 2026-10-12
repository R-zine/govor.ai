"""Allow-listed in-memory scene recipes.

The planner emits only deterministic identifiers and bounded transforms. It never accepts a file
path, URL, script, or model-authored asset reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

EnvironmentId = Literal["cafe", "supermarket", "airport", "home"]
CameraPreset = Literal["counter", "conversation", "wide"]
LightingPreset = Literal["warm", "daylight", "terminal", "home"]
TransitionKind = Literal["fade", "cut"]

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
class SceneObject:
    instance_id: str
    asset_id: str
    position: tuple[float, float, float]
    yaw_degrees: float = 0.0
    scale: float = 1.0

    def __post_init__(self) -> None:
        if not self.instance_id or len(self.instance_id) > 64:
            raise ValueError("scene object instance_id is invalid")
        if self.asset_id not in ALLOWED_ASSET_IDS:
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
        if not self.scene_id or len(self.scene_id) > 64:
            raise ValueError("scene_id is invalid")
        if any(not -20.0 <= component <= 20.0 for component in self.avatar_position):
            raise ValueError("avatar position is outside the accepted range")
        if not -360.0 <= self.avatar_yaw_degrees <= 360.0:
            raise ValueError("avatar yaw is outside the accepted range")
        if not 1 <= len(self.objects) <= 32:
            raise ValueError("scene must contain between one and 32 objects")
        instance_ids = [item.instance_id for item in self.objects]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("scene object instance IDs must be unique")


_SCENES: Final[MappingProxyType[str, SceneSpecification]] = MappingProxyType(
    {
        "cafe-ordering": SceneSpecification(
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
        "supermarket-shopping": SceneSpecification(
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
        "airport-travel": SceneSpecification(
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
        "home-conversation": SceneSpecification(
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
    """Resolve committed lesson context to a validated deterministic scene."""

    @property
    def supported_scenarios(self) -> tuple[str, ...]:
        return tuple(_SCENES)

    def plan(self, scenario_id: str) -> SceneSpecification:
        try:
            return _SCENES[scenario_id]
        except KeyError as error:
            raise ValueError("scenario_id has no allow-listed scene") from error
