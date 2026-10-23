from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path

import pytest
from govor_domain import IMPORT_LOCK_NAME, import_lesson_bundle, load_lesson_catalog

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LESSONS = ROOT / "assets" / "lesson-content"
SCENES = {"cafe", "supermarket", "airport", "home"}


def _catalog_directory(tmp_path: Path) -> Path:
    destination = tmp_path / "lessons"
    shutil.copytree(DEFAULT_LESSONS, destination)
    return destination


def _lesson_bytes(scenario_id: str, title: str) -> bytes:
    lesson = json.loads((DEFAULT_LESSONS / "cafe-ordering.json").read_text(encoding="utf-8"))
    lesson.update(
        {
            "scenario_id": scenario_id,
            "title": title,
            "display_order": 50,
        }
    )
    return (json.dumps(lesson, ensure_ascii=False) + "\n").encode()


def test_imports_a_json_lesson_additively(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    source = tmp_path / "chosen-name.json"
    source.write_bytes(_lesson_bytes("hotel-check-in", "Hotel check-in"))

    imported = import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert [item.scenario_id for item in imported] == ["hotel-check-in"]
    assert imported[0].destination == destination / "hotel-check-in.json"
    assert load_lesson_catalog(destination).get("hotel-check-in").title == "Hotel check-in"


def test_imports_multiple_json_lessons_from_nested_zip_entries(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    source = tmp_path / "lessons.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("bundle/hotel.json", _lesson_bytes("hotel-check-in", "Hotel"))
        archive.writestr("bundle/doctor.json", _lesson_bytes("doctor-visit", "Doctor"))

    imported = import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert {item.scenario_id for item in imported} == {"hotel-check-in", "doctor-visit"}
    assert (destination / "hotel-check-in.json").is_file()
    assert (destination / "doctor-visit.json").is_file()


@pytest.mark.parametrize("entry_name", ["../escape.json", "lesson.txt"])
def test_rejects_unsafe_or_non_json_zip_entries_without_writes(
    tmp_path: Path,
    entry_name: str,
) -> None:
    destination = _catalog_directory(tmp_path)
    original = sorted(path.name for path in destination.glob("*.json"))
    source = tmp_path / "lessons.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(entry_name, _lesson_bytes("hotel-check-in", "Hotel"))

    with pytest.raises(ValueError):
        import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert sorted(path.name for path in destination.glob("*.json")) == original


def test_rejects_an_invalid_bundle_atomically(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    source = tmp_path / "lessons.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("hotel.json", _lesson_bytes("hotel-check-in", "Hotel"))
        archive.writestr("broken.json", b"not JSON")

    with pytest.raises(ValueError, match="invalid lesson file"):
        import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert not (destination / "hotel-check-in.json").exists()


def test_rejects_duplicate_scenario_without_overwriting(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    original = (destination / "cafe-ordering.json").read_bytes()
    source = tmp_path / "replacement.json"
    source.write_bytes(_lesson_bytes("cafe-ordering", "Replacement"))

    with pytest.raises(ValueError, match="lesson already exists"):
        import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert (destination / "cafe-ordering.json").read_bytes() == original


def test_does_not_remove_another_import_process_lock(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    lock = destination / IMPORT_LOCK_NAME
    lock.write_text("another-process", encoding="utf-8")
    source = tmp_path / "hotel.json"
    source.write_bytes(_lesson_bytes("hotel-check-in", "Hotel"))

    with pytest.raises(ValueError, match="already in progress"):
        import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert lock.read_text(encoding="utf-8") == "another-process"


def test_rejects_missing_unsupported_and_oversized_sources(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    unsupported = tmp_path / "lesson.txt"
    unsupported.write_text("text", encoding="utf-8")
    oversized = tmp_path / "lesson.json"
    oversized.write_bytes(b" " * (4 * 1024 * 1024 + 1))

    with pytest.raises(ValueError, match="does not exist"):
        import_lesson_bundle(tmp_path / "missing.json", destination, allowed_scene_templates=SCENES)
    with pytest.raises(ValueError, match="select a .json or .zip"):
        import_lesson_bundle(unsupported, destination, allowed_scene_templates=SCENES)
    with pytest.raises(ValueError, match="exceeds 4 MiB"):
        import_lesson_bundle(oversized, destination, allowed_scene_templates=SCENES)


def test_rejects_empty_corrupt_and_oversized_zip_content(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, "w"):
        pass
    corrupt = tmp_path / "corrupt.zip"
    corrupt.write_bytes(b"not a zip")
    oversized = tmp_path / "oversized.zip"
    with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("oversized.json", b" " * 262_145)

    with pytest.raises(ValueError, match="between one and 64"):
        import_lesson_bundle(empty, destination, allowed_scene_templates=SCENES)
    with pytest.raises(ValueError, match="ZIP is invalid"):
        import_lesson_bundle(corrupt, destination, allowed_scene_templates=SCENES)
    with pytest.raises(ValueError, match="entry exceeds 256 KiB"):
        import_lesson_bundle(oversized, destination, allowed_scene_templates=SCENES)


def test_rejects_a_zip_with_excessive_directory_entries(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    source = tmp_path / "too-many-entries.zip"
    with zipfile.ZipFile(source, "w") as archive:
        for index in range(129):
            archive.writestr(f"folder-{index}/", b"")

    with pytest.raises(ValueError, match="too many archive entries"):
        import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)


def test_rejects_duplicate_bundle_ids_and_unknown_scene(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    duplicate = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(duplicate, "w") as archive:
        content = _lesson_bytes("hotel-check-in", "Hotel")
        archive.writestr("one.json", content)
        archive.writestr("two.json", content)
    unknown_scene = tmp_path / "unknown-scene.json"
    lesson = json.loads(_lesson_bytes("library-visit", "Library"))
    lesson["scene_template_id"] = "library"
    unknown_scene.write_text(json.dumps(lesson), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate scenario IDs"):
        import_lesson_bundle(duplicate, destination, allowed_scene_templates=SCENES)
    with pytest.raises(ValueError, match="unsupported scene template"):
        import_lesson_bundle(unknown_scene, destination, allowed_scene_templates=SCENES)


def test_publish_failure_rolls_back_the_whole_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = _catalog_directory(tmp_path)
    source = tmp_path / "lessons.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("hotel.json", _lesson_bytes("hotel-check-in", "Hotel"))
        archive.writestr("doctor.json", _lesson_bytes("doctor-visit", "Doctor"))
    original_rename = os.rename
    calls = 0

    def fail_second_publish(source_path: Path, destination_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publish failure")
        original_rename(source_path, destination_path)

    monkeypatch.setattr("govor_domain.lesson_import.os.rename", fail_second_publish)

    with pytest.raises(OSError, match="injected publish failure"):
        import_lesson_bundle(source, destination, allowed_scene_templates=SCENES)

    assert not (destination / "hotel-check-in.json").exists()
    assert not (destination / "doctor-visit.json").exists()
    assert not (destination / IMPORT_LOCK_NAME).exists()
