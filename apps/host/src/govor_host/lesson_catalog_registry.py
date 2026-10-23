"""Live, fail-closed access to immutable lesson catalog snapshots."""

from __future__ import annotations

import logging
from pathlib import Path

from govor_domain import IMPORT_LOCK_NAME, LessonCatalog, load_lesson_catalog
from govor_scene_planner import ScenePlanner

LOGGER = logging.getLogger("uvicorn.error")


class LessonCatalogRegistry:
    def __init__(
        self,
        directory: str | Path,
        initial: LessonCatalog,
        *,
        reload_enabled: bool,
    ) -> None:
        self._directory = Path(directory)
        self._catalog = initial
        self._reload_enabled = reload_enabled
        self._observed = self._fingerprint()
        self._last_reload_failed = False

    @property
    def catalog(self) -> LessonCatalog:
        return self._catalog

    @property
    def status(self) -> str:
        return "reload_error" if self._last_reload_failed else "ready"

    def refresh(self) -> LessonCatalog | None:
        """Replace the snapshot only when the complete changed directory is valid."""

        if not self._reload_enabled or (self._directory / IMPORT_LOCK_NAME).exists():
            return None
        fingerprint = self._fingerprint()
        if fingerprint == self._observed:
            return None
        self._observed = fingerprint
        try:
            catalog = load_lesson_catalog(self._directory)
            planner = ScenePlanner()
            for definition in catalog.lessons:
                planner.plan(definition.scene_template_id)
        except (OSError, ValueError) as error:
            self._last_reload_failed = True
            LOGGER.error(
                "lesson catalog reload rejected error_type=%s",
                type(error).__name__,
            )
            return None
        self._catalog = catalog
        self._last_reload_failed = False
        LOGGER.info("lesson catalog reloaded lesson_count=%d", len(catalog.lessons))
        return catalog

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
