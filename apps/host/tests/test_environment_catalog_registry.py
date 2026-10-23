from __future__ import annotations

import shutil
from pathlib import Path

from govor_domain import load_lesson_catalog
from govor_host.environment_catalog_registry import EnvironmentCatalogRegistry
from govor_host.orchestration import _scene_specification_payload
from govor_scene_planner import ScenePlanner

ROOT = Path(__file__).resolve().parents[3]


def test_registry_discovers_a_valid_environment_without_restart(tmp_path: Path) -> None:
    registry = EnvironmentCatalogRegistry(tmp_path, ScenePlanner(tmp_path))
    lessons = load_lesson_catalog(ROOT / "assets/lesson-content")
    shutil.copy(
        ROOT / "tests/fixtures/contracts/valid/environment-hotel-lobby.json",
        tmp_path / "hotel-lobby.json",
    )

    refreshed = registry.refresh(lessons)

    assert refreshed is not None
    assert registry.status == "ready"
    assert registry.planner.plan("hotel-lobby").scene_id == "hotel-lobby-v1"
    payload = _scene_specification_payload(registry.planner.plan("hotel-lobby"))
    assert payload.objects[0].asset_id is None
    assert payload.objects[0].primitive is not None
    assert payload.objects[0].primitive.color == "#70452A"


def test_registry_keeps_last_valid_snapshot_when_reload_is_invalid(tmp_path: Path) -> None:
    registry = EnvironmentCatalogRegistry(tmp_path, ScenePlanner(tmp_path))
    lessons = load_lesson_catalog(ROOT / "assets/lesson-content")
    (tmp_path / "broken.json").write_text("not JSON", encoding="utf-8")

    assert registry.refresh(lessons) is None
    assert registry.status == "reload_error"
    assert registry.planner.supported_templates == ("cafe", "supermarket", "airport", "home")
