"""SQLite adapter for structured learner progress.

Only exercise counters, vocabulary outcomes, settings, and adaptation reasons are stored.
Raw audio and transcript text never cross this boundary.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from govor_domain import (
    Difficulty,
    DifficultyChangeReason,
    LearnerSettings,
    LessonStatus,
    TeachingOutcome,
    TeachingState,
)


class SQLiteProgressRepository:
    SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(database_path)
        self._clock = clock or (lambda: datetime.now(UTC))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def get_settings(self) -> LearnerSettings:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT english_locale, starting_difficulty, spaced_review_enabled "
                "FROM learner_settings WHERE settings_id = 1"
            ).fetchone()
        if row is None:
            raise RuntimeError("learner settings row is missing")
        return LearnerSettings(
            english_locale=str(row["english_locale"]),
            starting_difficulty=Difficulty(str(row["starting_difficulty"])),
            spaced_review_enabled=bool(row["spaced_review_enabled"]),
        )

    def update_settings(self, settings: LearnerSettings) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE learner_settings
                SET english_locale = ?, starting_difficulty = ?, spaced_review_enabled = ?
                WHERE settings_id = 1
                """,
                (
                    settings.english_locale,
                    settings.starting_difficulty.value,
                    int(settings.spaced_review_enabled),
                ),
            )

    def load_or_start(self, scenario_id: str, exercise_count: int) -> tuple[TeachingState, bool]:
        if not 1 <= exercise_count <= 64:
            raise ValueError("exercise count must be between one and 64")
        settings = self.get_settings()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM scenario_progress WHERE scenario_id = ?",
                (scenario_id,),
            ).fetchone()
            if row is not None and bool(row["active"]):
                state = TeachingState(
                    exercise_index=int(row["exercise_index"]),
                    difficulty=Difficulty(str(row["difficulty"])),
                    attempts_on_exercise=int(row["attempts_on_exercise"]),
                    consecutive_first_try_successes=int(row["consecutive_first_try_successes"]),
                    successful_exercises=int(row["successful_exercises"]),
                    status=LessonStatus.IN_PROGRESS,
                    last_difficulty_reason=(
                        DifficultyChangeReason(str(row["last_difficulty_reason"]))
                        if row["last_difficulty_reason"] is not None
                        else None
                    ),
                )
                if state.exercise_index < exercise_count:
                    return state, True

            now = self._timestamp()
            connection.execute(
                """
                INSERT INTO scenario_progress (
                    scenario_id, exercise_index, difficulty, attempts_on_exercise,
                    consecutive_first_try_successes, successful_exercises,
                    completed_count, active, last_difficulty_reason, updated_at
                ) VALUES (?, 0, ?, 0, 0, 0, 0, 1, NULL, ?)
                ON CONFLICT(scenario_id) DO UPDATE SET
                    exercise_index = 0,
                    difficulty = excluded.difficulty,
                    attempts_on_exercise = 0,
                    consecutive_first_try_successes = 0,
                    successful_exercises = 0,
                    active = 1,
                    last_difficulty_reason = NULL,
                    updated_at = excluded.updated_at
                """,
                (scenario_id, settings.starting_difficulty.value, now),
            )
        return TeachingState(difficulty=settings.starting_difficulty), False

    def record_outcome(self, outcome: TeachingOutcome, state: TeachingState) -> None:
        """Atomically save one structured result without accepting transcript content."""

        now = self._now()
        timestamp = self._format_timestamp(now)
        with self._connect() as connection:
            current = connection.execute(
                "SELECT active FROM scenario_progress WHERE scenario_id = ?",
                (outcome.progress.scenario_id,),
            ).fetchone()
            if current is None:
                raise RuntimeError("scenario progress must be started before recording an outcome")
            newly_completed = state.status is LessonStatus.COMPLETED and bool(current["active"])
            connection.execute(
                """
                UPDATE scenario_progress SET
                    exercise_index = ?, difficulty = ?, attempts_on_exercise = ?,
                    consecutive_first_try_successes = ?, successful_exercises = ?,
                    completed_count = completed_count + ?, active = ?,
                    last_difficulty_reason = ?, updated_at = ?
                WHERE scenario_id = ?
                """,
                (
                    state.exercise_index,
                    state.difficulty.value,
                    state.attempts_on_exercise,
                    state.consecutive_first_try_successes,
                    state.successful_exercises,
                    int(newly_completed),
                    int(state.status is LessonStatus.IN_PROGRESS),
                    (
                        state.last_difficulty_reason.value
                        if state.last_difficulty_reason is not None
                        else None
                    ),
                    timestamp,
                    outcome.progress.scenario_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO exercise_history (
                    scenario_id, exercise_id, attempts, successes, help_requests,
                    last_practised_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(scenario_id, exercise_id) DO UPDATE SET
                    attempts = attempts + excluded.attempts,
                    successes = successes + excluded.successes,
                    help_requests = help_requests + excluded.help_requests,
                    last_practised_at = excluded.last_practised_at
                """,
                (
                    outcome.progress.scenario_id,
                    outcome.exercise_id,
                    int(outcome.attempt_recorded),
                    int(outcome.successful is True),
                    int(outcome.help_requested),
                    timestamp,
                ),
            )
            if outcome.attempt_recorded:
                for word in outcome.vocabulary:
                    self._record_vocabulary(
                        connection,
                        scenario_id=outcome.progress.scenario_id,
                        word=word,
                        successful=outcome.successful is True,
                        now=now,
                    )
            if state.last_difficulty_reason is not None:
                connection.execute(
                    """
                    INSERT INTO difficulty_history (
                        scenario_id, difficulty, reason, changed_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        outcome.progress.scenario_id,
                        state.difficulty.value,
                        state.last_difficulty_reason.value,
                        timestamp,
                    ),
                )

    def due_vocabulary(self, *, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("review limit must be between 1 and 100")
        if not self.get_settings().spaced_review_enabled:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT scenario_id, word, attempts, successes, next_review_at
                FROM vocabulary_history
                WHERE next_review_at <= ?
                ORDER BY next_review_at, scenario_id, word
                LIMIT ?
                """,
                (self._timestamp(), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def history(self) -> dict[str, Any]:
        with self._connect() as connection:
            scenarios = connection.execute(
                """
                SELECT scenario_id, exercise_index, difficulty, successful_exercises,
                       completed_count, active, last_difficulty_reason, updated_at
                FROM scenario_progress ORDER BY scenario_id
                """
            ).fetchall()
            exercises = connection.execute(
                """
                SELECT scenario_id, exercise_id, attempts, successes, help_requests,
                       last_practised_at
                FROM exercise_history ORDER BY scenario_id, exercise_id
                """
            ).fetchall()
            vocabulary = connection.execute(
                """
                SELECT scenario_id, word, attempts, successes, last_practised_at,
                       next_review_at
                FROM vocabulary_history ORDER BY scenario_id, word
                """
            ).fetchall()
            changes = connection.execute(
                """
                SELECT scenario_id, difficulty, reason, changed_at
                FROM difficulty_history ORDER BY change_id
                """
            ).fetchall()
        return {
            "schema_version": self.SCHEMA_VERSION,
            "settings": {
                "english_locale": self.get_settings().english_locale,
                "starting_difficulty": self.get_settings().starting_difficulty.value,
                "spaced_review_enabled": self.get_settings().spaced_review_enabled,
            },
            "scenarios": [dict(row) for row in scenarios],
            "exercises": [dict(row) for row in exercises],
            "vocabulary": [dict(row) for row in vocabulary],
            "difficulty_changes": [dict(row) for row in changes],
        }

    def delete_history(self) -> None:
        """Delete learner history while preserving the learner's explicit settings."""

        with self._connect() as connection:
            connection.execute("DELETE FROM difficulty_history")
            connection.execute("DELETE FROM vocabulary_history")
            connection.execute("DELETE FROM exercise_history")
            connection.execute("DELETE FROM scenario_progress")

    def delete_all_learner_data(self) -> None:
        """Delete history and restore all learner settings to product defaults."""

        defaults = LearnerSettings()
        with self._connect() as connection:
            connection.execute("PRAGMA secure_delete = ON")
            connection.execute("DELETE FROM difficulty_history")
            connection.execute("DELETE FROM vocabulary_history")
            connection.execute("DELETE FROM exercise_history")
            connection.execute("DELETE FROM scenario_progress")
            connection.execute(
                """
                UPDATE learner_settings
                SET english_locale = ?, starting_difficulty = ?, spaced_review_enabled = ?
                WHERE settings_id = 1
                """,
                (
                    defaults.english_locale,
                    defaults.starting_difficulty.value,
                    int(defaults.spaced_review_enabled),
                ),
            )
        with self._connect() as connection:
            connection.execute("VACUUM")

    def _record_vocabulary(
        self,
        connection: sqlite3.Connection,
        *,
        scenario_id: str,
        word: str,
        successful: bool,
        now: datetime,
    ) -> None:
        existing = connection.execute(
            """
            SELECT successes FROM vocabulary_history
            WHERE scenario_id = ? AND word = ?
            """,
            (scenario_id, word),
        ).fetchone()
        success_count = (int(existing["successes"]) if existing is not None else 0) + int(
            successful
        )
        review_days = (1, 3, 7, 14)[min(success_count, 3)] if successful else 0
        next_review = self._format_timestamp(now + timedelta(days=review_days))
        connection.execute(
            """
            INSERT INTO vocabulary_history (
                scenario_id, word, attempts, successes, last_practised_at, next_review_at
            ) VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(scenario_id, word) DO UPDATE SET
                attempts = attempts + 1,
                successes = successes + excluded.successes,
                last_practised_at = excluded.last_practised_at,
                next_review_at = excluded.next_review_at
            """,
            (scenario_id, word, int(successful), self._format_timestamp(now), next_review),
        )

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    schema_version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS learner_settings (
                    settings_id INTEGER PRIMARY KEY CHECK (settings_id = 1),
                    english_locale TEXT NOT NULL CHECK (english_locale IN ('en-GB', 'en-US')),
                    starting_difficulty TEXT NOT NULL
                        CHECK (starting_difficulty IN ('beginner', 'intermediate', 'advanced')),
                    spaced_review_enabled INTEGER NOT NULL
                        CHECK (spaced_review_enabled IN (0, 1))
                );
                CREATE TABLE IF NOT EXISTS scenario_progress (
                    scenario_id TEXT PRIMARY KEY,
                    exercise_index INTEGER NOT NULL CHECK (exercise_index >= 0),
                    difficulty TEXT NOT NULL
                        CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
                    attempts_on_exercise INTEGER NOT NULL CHECK (attempts_on_exercise >= 0),
                    consecutive_first_try_successes INTEGER NOT NULL
                        CHECK (consecutive_first_try_successes >= 0),
                    successful_exercises INTEGER NOT NULL CHECK (successful_exercises >= 0),
                    completed_count INTEGER NOT NULL CHECK (completed_count >= 0),
                    active INTEGER NOT NULL CHECK (active IN (0, 1)),
                    last_difficulty_reason TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exercise_history (
                    scenario_id TEXT NOT NULL,
                    exercise_id TEXT NOT NULL,
                    attempts INTEGER NOT NULL CHECK (attempts >= 0),
                    successes INTEGER NOT NULL CHECK (successes >= 0),
                    help_requests INTEGER NOT NULL CHECK (help_requests >= 0),
                    last_practised_at TEXT NOT NULL,
                    PRIMARY KEY (scenario_id, exercise_id)
                );
                CREATE TABLE IF NOT EXISTS vocabulary_history (
                    scenario_id TEXT NOT NULL,
                    word TEXT NOT NULL,
                    attempts INTEGER NOT NULL CHECK (attempts >= 0),
                    successes INTEGER NOT NULL CHECK (successes >= 0),
                    last_practised_at TEXT NOT NULL,
                    next_review_at TEXT NOT NULL,
                    PRIMARY KEY (scenario_id, word)
                );
                CREATE TABLE IF NOT EXISTS difficulty_history (
                    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    changed_at TEXT NOT NULL
                );
                """
            )
            version = connection.execute("SELECT schema_version FROM schema_metadata").fetchone()
            if version is None:
                connection.execute(
                    "INSERT INTO schema_metadata(schema_version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )
            elif int(version["schema_version"]) != self.SCHEMA_VERSION:
                raise RuntimeError("unsupported progress database schema version")
            connection.execute(
                """
                INSERT OR IGNORE INTO learner_settings (
                    settings_id, english_locale, starting_difficulty, spaced_review_enabled
                ) VALUES (1, 'en-GB', 'intermediate', 0)
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5.0)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            with connection:
                yield connection
        finally:
            connection.close()

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("progress clock must return a timezone-aware datetime")
        return value.astimezone(UTC)

    def _timestamp(self) -> str:
        return self._format_timestamp(self._now())

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
