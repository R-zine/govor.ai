"""Validated additive ZIP installation for local procedural environments."""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .environment_catalog import (
    ENVIRONMENT_LOCK_NAME,
    MAX_CUSTOM_ENVIRONMENTS,
    MAX_ENVIRONMENT_FILE_BYTES,
    environment_definition_from_mapping,
    load_environment_catalog,
)
from .scenes import ScenePlanner, SceneSpecification

_MAX_SOURCE_BYTES = 4 * 1024 * 1024
_MAX_ARCHIVE_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ImportedEnvironment:
    environment_id: str
    display_name: str
    destination: Path


@dataclass(frozen=True, slots=True)
class _Candidate:
    display_name: str
    specification: SceneSpecification
    content: bytes


def import_environment_bundle(
    source: str | Path,
    destination_directory: str | Path,
) -> tuple[ImportedEnvironment, ...]:
    source_path = Path(source)
    destination = Path(destination_directory)
    if not source_path.is_file():
        raise ValueError("the selected environment bundle does not exist")
    if source_path.suffix.lower() != ".zip":
        raise ValueError("select an environment .zip bundle")
    if source_path.stat().st_size > _MAX_SOURCE_BYTES:
        raise ValueError("the selected environment bundle exceeds 4 MiB")
    destination.mkdir(parents=True, exist_ok=True)
    candidates = _read_candidates(source_path)

    lock_path = destination / ENVIRONMENT_LOCK_NAME
    staged: list[tuple[Path, Path, _Candidate]] = []
    installed: list[Path] = []
    lock_acquired = False
    try:
        with lock_path.open("x", encoding="utf-8") as lock:
            lock.write(str(os.getpid()))
        lock_acquired = True
        existing = load_environment_catalog(destination)
        existing_ids = {item.environment_id for _, item in existing}
        protected_ids = set(ScenePlanner().supported_templates)
        candidate_ids = [item.specification.environment_id for item in candidates]
        candidate_scene_ids = [item.specification.scene_id for item in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("the environment bundle contains duplicate environment IDs")
        if len(candidate_scene_ids) != len(set(candidate_scene_ids)):
            raise ValueError("the environment bundle contains duplicate scene IDs")
        duplicates = sorted((existing_ids | protected_ids).intersection(candidate_ids))
        if duplicates:
            raise ValueError("environment already exists: " + ", ".join(duplicates))
        if len(existing) + len(candidates) > MAX_CUSTOM_ENVIRONMENTS:
            raise ValueError("the environment catalog cannot exceed 32 custom environments")

        for candidate in candidates:
            environment_id = candidate.specification.environment_id
            final_path = destination / f"{environment_id}.json"
            if final_path.exists():
                raise ValueError(f"environment file already exists: {final_path.name}")
            temporary = destination / f".{environment_id}.{uuid4().hex}.tmp"
            temporary.write_bytes(candidate.content)
            staged.append((temporary, final_path, candidate))
        for temporary, final_path, _ in staged:
            os.rename(temporary, final_path)
            installed.append(final_path)
        ScenePlanner(destination)
    except FileExistsError as error:
        raise ValueError("another environment import is already in progress") from error
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
        ImportedEnvironment(
            environment_id=candidate.specification.environment_id,
            display_name=candidate.display_name,
            destination=final_path,
        )
        for _, final_path, candidate in staged
    )


def _read_candidates(source: Path) -> tuple[_Candidate, ...]:
    try:
        with zipfile.ZipFile(source) as archive:
            archive_entries = archive.infolist()
            if len(archive_entries) > MAX_CUSTOM_ENVIRONMENTS * 2:
                raise ValueError("environment ZIP contains too many archive entries")
            entries = [item for item in archive_entries if not item.is_dir()]
            if not 1 <= len(entries) <= MAX_CUSTOM_ENVIRONMENTS:
                raise ValueError("environment ZIP must contain between one and 32 JSON files")
            if any(item.flag_bits & 0x1 for item in entries):
                raise ValueError("encrypted environment ZIP entries are not supported")
            if any(item.file_size > MAX_ENVIRONMENT_FILE_BYTES for item in entries):
                raise ValueError("an environment ZIP entry exceeds 256 KiB")
            if sum(item.file_size for item in entries) > _MAX_ARCHIVE_BYTES:
                raise ValueError("uncompressed environment ZIP content exceeds 4 MiB")

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
                    raise ValueError("environment ZIP contains an unsafe path")
                if path.suffix.lower() != ".json":
                    raise ValueError("environment ZIP may contain JSON files only")
                with archive.open(entry) as stream:
                    content = stream.read(MAX_ENVIRONMENT_FILE_BYTES + 1)
                candidates.append(_candidate_from_bytes(content, path.name))
            return tuple(candidates)
    except zipfile.BadZipFile as error:
        raise ValueError("the selected environment ZIP is invalid") from error


def _candidate_from_bytes(content: bytes, name: str) -> _Candidate:
    if len(content) > MAX_ENVIRONMENT_FILE_BYTES:
        raise ValueError(f"environment file exceeds 256 KiB: {name}")
    try:
        raw = json.loads(content.decode("utf-8"))
        display_name, specification = environment_definition_from_mapping(raw)
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ValueError(f"invalid environment file {name}: {error}") from error
    canonical = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return _Candidate(display_name, specification, canonical)
