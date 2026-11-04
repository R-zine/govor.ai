from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from govor_domain import IMPORT_LOCK_NAME, delete_lesson, load_lesson_catalog

SOURCE = Path(__file__).resolve().parents[3] / "assets/lesson-content"
SCENES = {"cafe", "supermarket", "airport", "home"}


@pytest.fixture
def lessons(tmp_path: Path) -> Path:
    destination = tmp_path / "lessons"
    shutil.copytree(SOURCE, destination)
    return destination


def test_deletion_resolves_content_id_and_preserves_other_files(lessons: Path) -> None:
    victim = lessons / "chosen-file-name.json"
    (lessons / "cafe-ordering.json").rename(victim)
    originals = {path.name: path.read_bytes() for path in lessons.glob("*.json") if path != victim}

    replacement = delete_lesson("cafe-ordering", lessons, allowed_scene_templates=SCENES)

    assert not victim.exists()
    assert len(replacement.lessons) == 3
    assert {path.name: path.read_bytes() for path in lessons.glob("*.json")} == originals
    assert load_lesson_catalog(lessons).lessons == replacement.lessons
    assert not (lessons / IMPORT_LOCK_NAME).exists()


@pytest.mark.parametrize("scenario_id", ["unknown-lesson", "../outside", "cafe-ordering.json"])
def test_unknown_or_path_like_id_cannot_delete_files(lessons: Path, scenario_id: str) -> None:
    originals = {path.name: path.read_bytes() for path in lessons.glob("*.json")}

    with pytest.raises(ValueError, match="unknown guided scenario"):
        delete_lesson(scenario_id, lessons, allowed_scene_templates=SCENES)

    assert {path.name: path.read_bytes() for path in lessons.glob("*.json")} == originals


def test_last_lesson_is_protected(tmp_path: Path) -> None:
    shutil.copy2(SOURCE / "cafe-ordering.json", tmp_path)

    with pytest.raises(ValueError, match="last remaining lesson"):
        delete_lesson("cafe-ordering", tmp_path, allowed_scene_templates=SCENES)

    assert len(load_lesson_catalog(tmp_path).lessons) == 1


def test_deletion_respects_existing_import_lock(lessons: Path) -> None:
    lock = lessons / IMPORT_LOCK_NAME
    lock.write_text("other-process", encoding="utf-8")

    with pytest.raises(ValueError, match="already in progress"):
        delete_lesson("cafe-ordering", lessons, allowed_scene_templates=SCENES)

    assert lock.read_text(encoding="utf-8") == "other-process"
    assert (lessons / "cafe-ordering.json").exists()


def test_invalid_remaining_content_does_not_partially_delete(lessons: Path) -> None:
    (lessons / "broken.json").write_text("not JSON", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid lesson file"):
        delete_lesson("cafe-ordering", lessons, allowed_scene_templates=SCENES)

    assert (lessons / "cafe-ordering.json").exists()
    assert not (lessons / IMPORT_LOCK_NAME).exists()


def test_file_permission_failure_keeps_lesson_and_releases_lock(
    lessons: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    victim = lessons / "cafe-ordering.json"
    original_unlink = Path.unlink

    def denied_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path == victim:
            raise PermissionError("test denial")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", denied_unlink)

    with pytest.raises(PermissionError):
        delete_lesson("cafe-ordering", lessons, allowed_scene_templates=SCENES)

    assert len(load_lesson_catalog(lessons).lessons) == 4
    assert not (lessons / IMPORT_LOCK_NAME).exists()
