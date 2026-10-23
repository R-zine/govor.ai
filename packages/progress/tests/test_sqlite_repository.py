from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from govor_domain import (
    DetectedLanguage,
    Difficulty,
    LearnerIntent,
    LearnerSettings,
    TeachingEngine,
    TeachingState,
    load_lesson_catalog,
)
from govor_progress import SQLiteProgressRepository

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_lesson_catalog(ROOT / "assets" / "lesson-content")


def repository(tmp_path) -> SQLiteProgressRepository:  # type: ignore[no-untyped-def]
    return SQLiteProgressRepository(tmp_path / "progress.sqlite3", clock=lambda: NOW)


def load_progress(
    progress: SQLiteProgressRepository,
    scenario_id: str,
) -> tuple[TeachingState, bool]:
    lesson = CATALOG.get(scenario_id)
    return progress.load_or_start(scenario_id, len(lesson.exercises))


def test_interrupted_session_resumes_from_saved_exercise(tmp_path) -> None:  # type: ignore[no-untyped-def]
    first_repository = repository(tmp_path)
    state, resumed = load_progress(first_repository, "cafe-ordering")
    engine = TeachingEngine(CATALOG.get("cafe-ordering"), state, resumed=resumed)
    outcome = engine.evaluate(
        "I would like coffee, please.",
        DetectedLanguage.ENGLISH,
        LearnerIntent.ENGLISH_ANSWER,
    )
    first_repository.record_outcome(outcome, engine.state)

    restored_state, restored = load_progress(repository(tmp_path), "cafe-ordering")
    restored_engine = TeachingEngine(CATALOG.get("cafe-ordering"), restored_state, resumed=restored)

    assert restored
    assert restored_state.exercise_index == 1
    assert restored_engine.initial_prompt().startswith("Welcome back.")
    assert "anything else" in restored_engine.initial_prompt().lower()


def test_history_tracks_attempts_help_vocabulary_and_completion_without_transcript(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    progress = repository(tmp_path)
    state, _ = load_progress(progress, "cafe-ordering")
    engine = TeachingEngine(CATALOG.get("cafe-ordering"), state)
    learner_text = "I would like coffee, please. PRIVATE-TRANSCRIPT"
    inputs = [
        (
            "Не разбирам.",
            DetectedLanguage.BULGARIAN,
            LearnerIntent.BULGARIAN_CLARIFICATION,
        ),
        (
            learner_text,
            DetectedLanguage.ENGLISH,
            LearnerIntent.ENGLISH_ANSWER,
        ),
        (
            "That is all, thank you.",
            DetectedLanguage.ENGLISH,
            LearnerIntent.ENGLISH_ANSWER,
        ),
        (
            "For here, please.",
            DetectedLanguage.ENGLISH,
            LearnerIntent.ENGLISH_ANSWER,
        ),
    ]
    for text, language, intent in inputs:
        outcome = engine.evaluate(text, language, intent)
        progress.record_outcome(outcome, engine.state)

    history = progress.history()
    serialized = json.dumps(history, ensure_ascii=False)

    assert history["scenarios"][0]["completed_count"] == 1
    assert sum(item["help_requests"] for item in history["exercises"]) == 1
    assert history["vocabulary"]
    assert "PRIVATE-TRANSCRIPT" not in serialized
    assert "audio" not in serialized.casefold()


def test_settings_due_review_export_and_delete(tmp_path) -> None:  # type: ignore[no-untyped-def]
    progress = repository(tmp_path)
    progress.update_settings(
        LearnerSettings(
            english_locale="en-US",
            starting_difficulty=Difficulty.BEGINNER,
            spaced_review_enabled=True,
        )
    )
    state, _ = load_progress(progress, "supermarket-shopping")
    engine = TeachingEngine(CATALOG.get("supermarket-shopping"), state)
    failed = engine.evaluate(
        "I need something.",
        DetectedLanguage.ENGLISH,
        LearnerIntent.ENGLISH_ANSWER,
    )
    progress.record_outcome(failed, engine.state)

    assert progress.get_settings().english_locale == "en-US"
    assert progress.due_vocabulary()
    assert progress.history()["settings"]["spaced_review_enabled"] is True

    progress.delete_history()

    assert progress.history()["scenarios"] == []
    assert progress.history()["vocabulary"] == []
    assert progress.get_settings().english_locale == "en-US"


def test_delete_all_learner_data_restores_default_settings(tmp_path) -> None:  # type: ignore[no-untyped-def]
    progress = repository(tmp_path)
    progress.update_settings(
        LearnerSettings(
            english_locale="en-US",
            starting_difficulty=Difficulty.BEGINNER,
            spaced_review_enabled=True,
        )
    )
    load_progress(progress, "airport-travel")

    progress.delete_all_learner_data()

    assert progress.history()["scenarios"] == []
    assert progress.history()["vocabulary"] == []
    assert progress.get_settings() == LearnerSettings()
    assert b"airport-travel" not in progress.path.read_bytes()
