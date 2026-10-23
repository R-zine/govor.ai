"""Live, fail-closed access to immutable environment planner snapshots."""

from __future__ import annotations

import logging
from pathlib import Path

from govor_domain import LessonCatalog
from govor_scene_planner import ENVIRONMENT_LOCK_NAME, ScenePlanner

LOGGER = logging.getLogger("uvicorn.error")


class EnvironmentCatalogRegistry:
    def __init__(self, directory: str | Path, initial: ScenePlanner) -> None:
        self._directory = Path(directory)
        self._planner = initial
        self._observed = self._fingerprint()
        self._last_reload_failed = False

    @property
    def planner(self) -> ScenePlanner:
        return self._planner

    @property
    def status(self) -> str:
        return "reload_error" if self._last_reload_failed else "ready"

    def refresh(self, lessons: LessonCatalog) -> ScenePlanner | None:
        if (self._directory / ENVIRONMENT_LOCK_NAME).exists():
            return None
        fingerprint = self._fingerprint()
        if fingerprint == self._observed:
            return None
        self._observed = fingerprint
        try:
            planner = ScenePlanner(self._directory)
            for definition in lessons.lessons:
                planner.plan(definition.scene_template_id)
        except (OSError, ValueError) as error:
            self._last_reload_failed = True
            LOGGER.error("environment catalog reload rejected error_type=%s", type(error).__name__)
            return None
        self._planner = planner
        self._last_reload_failed = False
        LOGGER.info(
            "environment catalog reloaded environment_count=%d",
            len(planner.supported_templates),
        )
        return planner

    def _fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        try:
            return tuple(
                (path.name, stat.st_size, stat.st_mtime_ns)
                for path in sorted(self._directory.glob("*.json"))
                if path.is_file()
                for stat in (path.stat(),)
            )
        except OSError:
            return ()
