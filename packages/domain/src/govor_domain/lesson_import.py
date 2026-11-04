"""Validated imports and session-confirmed deletion of local lesson content."""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .lesson_catalog import LessonCatalog, lesson_definition_from_mapping, load_lesson_catalog
from .teaching import LessonDefinition

_MAX_SOURCE_BYTES = 4 * 1024 * 1024
_MAX_LESSON_BYTES = 262_144
_MAX_ARCHIVE_FILES = 64
_MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
IMPORT_LOCK_NAME = ".lesson-import.lock"


@dataclass(frozen=True, slots=True)
class ImportedLesson:
    scenario_id: str
    title: str
    destination: Path


@dataclass(frozen=True, slots=True)
class _Candidate:
    definition: LessonDefinition
    content: bytes


def import_lesson_bundle(
    source: str | Path,
    destination_directory: str | Path,
    *,
    allowed_scene_templates: set[str] | frozenset[str],
) -> tuple[ImportedLesson, ...]:
    """Validate and add a JSON lesson or ZIP bundle without overwriting existing content."""

    source_path = Path(source)
    destination = Path(destination_directory)
    if not source_path.is_file():
        raise ValueError("the selected lesson file does not exist")
    if source_path.stat().st_size > _MAX_SOURCE_BYTES:
        raise ValueError("the selected lesson file exceeds 4 MiB")
    destination.mkdir(parents=True, exist_ok=True)

    candidates = _read_candidates(source_path)
    lock_path = destination / IMPORT_LOCK_NAME
    staged: list[tuple[Path, Path, _Candidate]] = []
    installed: list[Path] = []
    lock_acquired = False
    try:
        with lock_path.open("x", encoding="utf-8") as lock:
            lock.write(str(os.getpid()))
        lock_acquired = True
        existing = load_lesson_catalog(destination)
        existing_ids = {lesson.scenario_id for lesson in existing.lessons}
        candidate_ids = [candidate.definition.scenario_id for candidate in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("the selected bundle contains duplicate scenario IDs")
        duplicates = sorted(existing_ids.intersection(candidate_ids))
        if duplicates:
            raise ValueError("lesson already exists: " + ", ".join(duplicates))

        combined = LessonCatalog((*existing.lessons, *(item.definition for item in candidates)))
        for definition in combined.lessons:
            if definition.scene_template_id not in allowed_scene_templates:
                raise ValueError(
                    f"lesson {definition.scenario_id} uses an unsupported scene template"
                )

        for candidate in candidates:
            final_path = destination / f"{candidate.definition.scenario_id}.json"
            if final_path.exists():
                raise ValueError(f"lesson file already exists: {final_path.name}")
            temporary = destination / f".{candidate.definition.scenario_id}.{uuid4().hex}.tmp"
            temporary.write_bytes(candidate.content)
            staged.append((temporary, final_path, candidate))
        for temporary, final_path, _ in staged:
            os.rename(temporary, final_path)
            installed.append(final_path)
    except FileExistsError as error:
        raise ValueError("another lesson import is already in progress") from error
    except Exception:
        for path in installed:
            path.unlink(missing_ok=True)
        raise
    finally:
        for temporary, _, _ in staged:
            temporary.unlink(missing_ok=True)
        if lock_acquired:
            lock_path.unlink(missing_ok=True)

    return tuple(
        ImportedLesson(
            scenario_id=candidate.definition.scenario_id,
            title=candidate.definition.title,
            destination=final_path,
        )
        for _, final_path, candidate in staged
    )


def delete_lesson(
    scenario_id: str,
    destination_directory: str | Path,
    *,
    allowed_scene_templates: set[str] | frozenset[str],
) -> LessonCatalog:
    """Remove exactly one validated lesson while retaining a usable, nonempty catalog."""

    destination = Path(destination_directory).resolve()
    lock_path = destination / IMPORT_LOCK_NAME
    lock_acquired = False
    try:
        with lock_path.open("x", encoding="utf-8") as lock:
            lock.write(str(os.getpid()))
        lock_acquired = True
        existing = load_lesson_catalog(destination)
        existing.get(scenario_id)
        remaining = [lesson for lesson in existing.lessons if lesson.scenario_id != scenario_id]
        if not remaining:
            raise ValueError("Create another lesson before deleting the last remaining lesson.")
        replacement = LessonCatalog(remaining)
        if any(lesson.scene_template_id not in allowed_scene_templates for lesson in remaining):
            raise ValueError("The remaining lessons reference an unavailable environment.")

        # File names are local loader data, never derived from a phone-supplied path or ID.
        for path in destination.glob("*.json"):
            if not path.is_file():
                continue
            definition = lesson_definition_from_mapping(
                json.loads(path.read_text(encoding="utf-8"))
            )
            if definition.scenario_id != scenario_id:
                continue
            if path.is_symlink() or path.resolve().parent != destination:
                raise ValueError("Linked lesson files cannot be deleted through the application.")
            path.unlink()
            return replacement
        raise ValueError("The lesson file is no longer available.")
    except FileExistsError as error:
        raise ValueError("Another lesson content change is already in progress.") from error
    finally:
        if lock_acquired:
            lock_path.unlink(missing_ok=True)


def _read_candidates(source: Path) -> tuple[_Candidate, ...]:
    suffix = source.suffix.lower()
    if suffix == ".json":
        return (_candidate_from_bytes(source.read_bytes(), source.name),)
    if suffix != ".zip":
        raise ValueError("select a .json or .zip lesson file")

    try:
        with zipfile.ZipFile(source) as archive:
            archive_entries = archive.infolist()
            if len(archive_entries) > _MAX_ARCHIVE_FILES * 2:
                raise ValueError("lesson ZIP contains too many archive entries")
            entries = [item for item in archive_entries if not item.is_dir()]
            if not 1 <= len(entries) <= _MAX_ARCHIVE_FILES:
                raise ValueError("lesson ZIP must contain between one and 64 files")
            if any(item.flag_bits & 0x1 for item in entries):
                raise ValueError("encrypted lesson ZIP entries are not supported")
            if any(item.file_size > _MAX_LESSON_BYTES for item in entries):
                raise ValueError("a lesson ZIP entry exceeds 256 KiB")
            if sum(item.file_size for item in entries) > _MAX_ARCHIVE_BYTES:
                raise ValueError("uncompressed lesson ZIP content exceeds 4 MiB")

            candidates: list[_Candidate] = []
            for entry in entries:
                normalized_name = entry.filename.replace("\\", "/")
                path = PurePosixPath(normalized_name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.name
                    or ":" in path.parts[0]
                ):
                    raise ValueError("lesson ZIP contains an unsafe path")
                if path.suffix.lower() != ".json":
                    raise ValueError("lesson ZIP may contain JSON files only")
                with archive.open(entry) as stream:
                    content = stream.read(_MAX_LESSON_BYTES + 1)
                if len(content) > _MAX_LESSON_BYTES:
                    raise ValueError("a lesson ZIP entry exceeds 256 KiB")
                candidates.append(_candidate_from_bytes(content, path.name))
            return tuple(candidates)
    except zipfile.BadZipFile as error:
        raise ValueError("the selected lesson ZIP is invalid") from error


def _candidate_from_bytes(content: bytes, name: str) -> _Candidate:
    if len(content) > _MAX_LESSON_BYTES:
        raise ValueError(f"lesson file exceeds 256 KiB: {name}")
    try:
        raw = json.loads(content.decode("utf-8"))
        definition = lesson_definition_from_mapping(raw)
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ValueError(f"invalid lesson file {name}: {error}") from error
    return _Candidate(definition=definition, content=content)
