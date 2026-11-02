from __future__ import annotations

from pathlib import Path

import pytest
from govor_domain import (
    DetectedLanguage,
    Difficulty,
    DifficultyChangeReason,
    LearnerIntent,
    LessonStatus,
    TeachingEngine,
    TeachingState,
    load_lesson_catalog,
)

ROOT = Path(__file__).resolve().parents[3]
CATALOG = load_lesson_catalog(ROOT / "assets" / "lesson-content")


def test_four_scenarios_define_complete_guidance() -> None:
    assert {lesson.scenario_id for lesson in CATALOG.lessons} == {
        "cafe-ordering",
        "supermarket-shopping",
        "airport-travel",
        "home-conversation",
    }
    for lesson in CATALOG.lessons:
        assert len(lesson.exercises) >= 3
        assert len(lesson.difficulty_descriptions) == 3
        assert lesson.objectives
        assert lesson.target_vocabulary
        assert lesson.examples
        assert lesson.common_misunderstandings
        assert lesson.completion_condition
        assert all(exercise.expected_intent for exercise in lesson.exercises)
        assert all(exercise.explanation_bg for exercise in lesson.exercises)


def test_help_and_bulgarian_production_do_not_advance() -> None:
    engine = TeachingEngine(CATALOG.get("cafe-ordering"))

    help_outcome = engine.evaluate(
        "Какво означава order?",
        DetectedLanguage.BULGARIAN,
        LearnerIntent.VOCABULARY_EXPLANATION,
    )
    bulgarian_answer = engine.evaluate(
        "Искам кафе, моля.",
        DetectedLanguage.BULGARIAN,
        LearnerIntent.ENGLISH_ANSWER,
    )

    assert help_outcome.help_requested
    assert bulgarian_answer.help_requested
    assert engine.state.exercise_index == 0
    assert engine.state.attempts_on_exercise == 0
    assert "не завършен английски отговор" in bulgarian_answer.reply_text


def test_repeated_difficulty_lowers_level_with_an_explainable_reason() -> None:
    engine = TeachingEngine(CATALOG.get("cafe-ordering"))

    first = engine.evaluate("Coffee.", DetectedLanguage.ENGLISH, LearnerIntent.ENGLISH_ANSWER)
    second = engine.evaluate("Coffee.", DetectedLanguage.ENGLISH, LearnerIntent.ENGLISH_ANSWER)

    assert not first.successful
    assert not second.successful
    assert engine.state.exercise_index == 0
    assert engine.state.difficulty is Difficulty.BEGINNER
    assert second.progress.difficulty_change_reason is DifficultyChangeReason.REPEATED_DIFFICULTY
    assert "I would like" in second.reply_text
    assert "Кажете" in second.reply_text


def test_consistent_first_try_success_raises_difficulty() -> None:
    engine = TeachingEngine(
        CATALOG.get("cafe-ordering"),
        TeachingState(difficulty=Difficulty.BEGINNER),
    )

    engine.evaluate(
        "I would like coffee, please.",
        DetectedLanguage.ENGLISH,
        LearnerIntent.ENGLISH_ANSWER,
    )
    second = engine.evaluate(
        "That is all, thank you.",
        DetectedLanguage.ENGLISH,
        LearnerIntent.ENGLISH_ANSWER,
    )

    assert engine.state.difficulty is Difficulty.INTERMEDIATE
    assert (
        second.progress.difficulty_change_reason
        is DifficultyChangeReason.CONSISTENT_FIRST_TRY_SUCCESS
    )


@pytest.mark.parametrize(
    "answer",
    (
        "I am flying to New York.",
        "My flight to Sofia leaves tonight.",
        "I am going to Paris.",
        "My destination is Rio de Janeiro.",
    ),
)
def test_destination_exercise_accepts_a_learner_chosen_city(answer: str) -> None:
    engine = TeachingEngine(CATALOG.get("airport-travel"))

    outcome = engine.evaluate(answer, DetectedLanguage.ENGLISH, LearnerIntent.ENGLISH_ANSWER)

    assert outcome.successful
    assert engine.state.exercise_index == 1


@pytest.mark.parametrize(
    "answer",
    ("I am flying to.", "My destination is.", "I am flying from New York."),
)
def test_destination_exercise_requires_a_value_after_the_direction(answer: str) -> None:
    engine = TeachingEngine(CATALOG.get("airport-travel"))

    outcome = engine.evaluate(answer, DetectedLanguage.ENGLISH, LearnerIntent.ENGLISH_ANSWER)

    assert outcome.successful is False
    assert engine.state.exercise_index == 0


@pytest.mark.parametrize(
    ("scenario_id", "answers"),
    [
        (
            "cafe-ordering",
            (
                "I would like coffee, please.",
                "That is all, thank you.",
                "For here, please.",
            ),
        ),
        (
            "supermarket-shopping",
            (
                "Where can I find the milk?",
                "I would like a kilo of apples.",
                "Yes, I would like a bag.",
            ),
        ),
        (
            "airport-travel",
            (
                "I am flying to London.",
                "I have one small bag as hand luggage.",
                "Where can I find the gate?",
            ),
        ),
        (
            "home-conversation",
            (
                "I usually make breakfast in the morning.",
                "Could you help me with dinner?",
                "Let's watch a film this evening.",
            ),
        ),
    ],
)
def test_complete_guided_lesson_finishes_every_scenario(
    scenario_id: str,
    answers: tuple[str, str, str],
) -> None:
    engine = TeachingEngine(CATALOG.get(scenario_id))

    outcomes = [
        engine.evaluate(answer, DetectedLanguage.ENGLISH, LearnerIntent.ENGLISH_ANSWER)
        for answer in answers
    ]

    assert all(outcome.successful for outcome in outcomes)
    assert outcomes[-1].progress.status is LessonStatus.COMPLETED
    assert outcomes[-1].progress.successful_exercises == 3
    assert "completed" in outcomes[-1].reply_text
    with pytest.raises(ValueError, match="already complete"):
        engine.evaluate("again", DetectedLanguage.ENGLISH, LearnerIntent.ENGLISH_ANSWER)


def test_unknown_scenario_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown guided scenario"):
        CATALOG.get("not-a-scenario")
