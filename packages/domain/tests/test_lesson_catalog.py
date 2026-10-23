from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from govor_domain import load_lesson_catalog

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LESSONS = ROOT / "assets" / "lesson-content"


def test_default_catalog_loads_in_display_order() -> None:
    catalog = load_lesson_catalog(DEFAULT_LESSONS)

    assert catalog.default_scenario_id == "cafe-ordering"
    assert [lesson.scenario_id for lesson in catalog.lessons] == [
        "cafe-ordering",
        "supermarket-shopping",
        "airport-travel",
        "home-conversation",
    ]
    assert catalog.get("cafe-ordering").scene_template_id == "cafe"


def test_adding_a_json_file_adds_a_lesson_without_code_changes(tmp_path: Path) -> None:
    for source in DEFAULT_LESSONS.glob("*.json"):
        shutil.copy2(source, tmp_path / source.name)
    additional = json.loads((DEFAULT_LESSONS / "cafe-ordering.json").read_text(encoding="utf-8"))
    additional.update(
        {
            "scenario_id": "cafe-breakfast",
            "title": "Breakfast at a café",
            "description": "Order breakfast politely.",
            "display_order": 2,
        }
    )
    (tmp_path / "cafe-breakfast.json").write_text(
        json.dumps(additional, ensure_ascii=False),
        encoding="utf-8",
    )

    catalog = load_lesson_catalog(tmp_path)

    assert len(catalog.lessons) == 5
    assert catalog.get("cafe-breakfast").title == "Breakfast at a café"
    assert catalog.get("cafe-breakfast").scene_template_id == "cafe"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"unexpected": True}, "fields do not match"),
        ({"schema_version": 2}, "unsupported lesson schema version"),
        ({"exercises": []}, "exercises must contain"),
        ({"scene_template_id": "../../download"}, "scene template id"),
    ],
)
def test_invalid_lesson_file_fails_the_catalog_at_startup(
    tmp_path: Path,
    mutation: dict[str, object],
    message: str,
) -> None:
    lesson = json.loads((DEFAULT_LESSONS / "cafe-ordering.json").read_text(encoding="utf-8"))
    lesson.update(mutation)
    (tmp_path / "invalid.json").write_text(json.dumps(lesson), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_lesson_catalog(tmp_path)


def test_duplicate_scenario_ids_are_rejected(tmp_path: Path) -> None:
    source = DEFAULT_LESSONS / "cafe-ordering.json"
    shutil.copy2(source, tmp_path / "first.json")
    shutil.copy2(source, tmp_path / "second.json")

    with pytest.raises(ValueError, match="duplicate lesson scenario id"):
        load_lesson_catalog(tmp_path)
