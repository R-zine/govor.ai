"""Strict JSON-backed guided-lesson catalog.

The loader is framework independent. It validates local text content before constructing the
immutable domain definitions consumed by teaching, progress, rendering, and the Android catalog.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

from .teaching import (
    CommonMisunderstanding,
    ExampleInteraction,
    ExerciseType,
    LessonDefinition,
    LessonExercise,
)

_MAX_LESSON_FILES = 64
_MAX_LESSON_FILE_BYTES = 262_144
_ROOT_FIELDS = {
    "schema_version",
    "scenario_id",
    "title",
    "description",
    "display_order",
    "scene_template_id",
    "objectives",
    "target_vocabulary",
    "difficulty_descriptions",
    "examples",
    "common_misunderstandings",
    "exercises",
    "completion_condition",
}
_EXAMPLE_FIELDS = {"teacher", "learner"}
_MISUNDERSTANDING_FIELDS = {"pattern", "correction", "explanation_bg"}
_EXERCISE_FIELDS = {
    "exercise_id",
    "exercise_type",
    "goal",
    "expected_intent",
    "prompts",
    "accepted_patterns",
    "target_vocabulary",
    "gentle_correction",
    "explanation_bg",
}


class LessonCatalog:
    """Immutable, ordered collection of validated lesson definitions."""

    def __init__(self, lessons: Iterable[LessonDefinition]) -> None:
        ordered = tuple(
            sorted(
                lessons,
                key=lambda item: (item.display_order, item.title, item.scenario_id),
            )
        )
        if not 1 <= len(ordered) <= _MAX_LESSON_FILES:
            raise ValueError("lesson catalog must contain between one and 64 lessons")
        by_id: dict[str, LessonDefinition] = {}
        for lesson in ordered:
            if lesson.scenario_id in by_id:
                raise ValueError(f"duplicate lesson scenario id: {lesson.scenario_id}")
            by_id[lesson.scenario_id] = lesson
        self._lessons = ordered
        self._by_id: Mapping[str, LessonDefinition] = MappingProxyType(by_id)

    @property
    def lessons(self) -> tuple[LessonDefinition, ...]:
        return self._lessons

    @property
    def default_scenario_id(self) -> str:
        return self._lessons[0].scenario_id

    def get(self, scenario_id: str) -> LessonDefinition:
        try:
            return self._by_id[scenario_id]
        except KeyError as error:
            raise ValueError("unknown guided scenario") from error


def load_lesson_catalog(directory: str | Path) -> LessonCatalog:
    """Load all JSON lesson files once, failing before the host starts on invalid content."""

    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"lesson directory does not exist: {root}")
    paths = sorted(path for path in root.glob("*.json") if path.is_file())
    if not paths:
        raise ValueError(f"lesson directory contains no JSON lessons: {root}")
    if len(paths) > _MAX_LESSON_FILES:
        raise ValueError("lesson directory contains more than 64 JSON lessons")

    lessons: list[LessonDefinition] = []
    for path in paths:
        if path.stat().st_size > _MAX_LESSON_FILE_BYTES:
            raise ValueError(f"lesson file exceeds 256 KiB: {path.name}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            lessons.append(lesson_definition_from_mapping(raw))
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid lesson file {path.name}: {error}") from error
    return LessonCatalog(lessons)


def lesson_definition_from_mapping(value: object) -> LessonDefinition:
    root = _object(value, "lesson", _ROOT_FIELDS)
    if _integer(root["schema_version"], "schema_version") != 1:
        raise ValueError("unsupported lesson schema version")

    difficulty = _strings(root["difficulty_descriptions"], "difficulty_descriptions", maximum=3)
    if len(difficulty) != 3:
        raise ValueError("difficulty_descriptions must contain exactly three values")

    examples = tuple(
        ExampleInteraction(
            teacher=_string(item["teacher"], "examples.teacher"),
            learner=_string(item["learner"], "examples.learner"),
        )
        for item in _objects(root["examples"], "examples", _EXAMPLE_FIELDS, maximum=16)
    )
    misunderstandings = tuple(
        CommonMisunderstanding(
            pattern=_string(item["pattern"], "common_misunderstandings.pattern"),
            correction=_string(item["correction"], "common_misunderstandings.correction"),
            explanation_bg=_string(
                item["explanation_bg"], "common_misunderstandings.explanation_bg"
            ),
        )
        for item in _objects(
            root["common_misunderstandings"],
            "common_misunderstandings",
            _MISUNDERSTANDING_FIELDS,
            maximum=32,
        )
    )

    exercises: list[LessonExercise] = []
    for item in _objects(root["exercises"], "exercises", _EXERCISE_FIELDS, maximum=64):
        prompts = _strings(item["prompts"], "exercises.prompts", maximum=3)
        if len(prompts) != 3:
            raise ValueError("each exercise must contain exactly three prompts")
        raw_patterns = item["accepted_patterns"]
        if not isinstance(raw_patterns, list) or not 1 <= len(raw_patterns) <= 32:
            raise ValueError("accepted_patterns must contain between one and 32 patterns")
        patterns = tuple(
            _strings(pattern, "accepted_patterns pattern", maximum=16) for pattern in raw_patterns
        )
        try:
            exercise_type = ExerciseType(_string(item["exercise_type"], "exercise_type"))
        except ValueError as error:
            raise ValueError("exercise_type is unsupported") from error
        exercises.append(
            LessonExercise(
                exercise_id=_string(item["exercise_id"], "exercise_id", maximum=64),
                exercise_type=exercise_type,
                goal=_string(item["goal"], "goal"),
                expected_intent=_string(item["expected_intent"], "expected_intent"),
                prompts=(prompts[0], prompts[1], prompts[2]),
                accepted_patterns=patterns,
                target_vocabulary=_strings(
                    item["target_vocabulary"], "exercise target_vocabulary", maximum=64
                ),
                gentle_correction=_string(item["gentle_correction"], "gentle_correction"),
                explanation_bg=_string(item["explanation_bg"], "explanation_bg"),
            )
        )

    return LessonDefinition(
        scenario_id=_string(root["scenario_id"], "scenario_id", maximum=64),
        title=_string(root["title"], "title", maximum=128),
        description=_string(root["description"], "description", maximum=512),
        display_order=_integer(root["display_order"], "display_order"),
        scene_template_id=_string(root["scene_template_id"], "scene_template_id", maximum=64),
        objectives=_strings(root["objectives"], "objectives", maximum=16),
        target_vocabulary=_strings(root["target_vocabulary"], "target_vocabulary", maximum=64),
        difficulty_descriptions=(difficulty[0], difficulty[1], difficulty[2]),
        examples=examples,
        common_misunderstandings=misunderstandings,
        exercises=tuple(exercises),
        completion_condition=_string(root["completion_condition"], "completion_condition"),
    )


def _object(value: object, name: str, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise TypeError(f"{name} must be an object")
    result = cast(dict[str, object], value)
    actual = set(result)
    if actual != fields:
        missing = sorted(fields - actual)
        extra = sorted(actual - fields)
        raise ValueError(f"{name} fields do not match; missing={missing}, extra={extra}")
    return result


def _objects(
    value: object,
    name: str,
    fields: set[str],
    *,
    maximum: int,
) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{name} must contain between one and {maximum} objects")
    return tuple(_object(item, name, fields) for item in value)


def _strings(value: object, name: str, *, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{name} must contain between one and {maximum} strings")
    return tuple(_string(item, name, maximum=1_024) for item in value)


def _string(value: object, name: str, *, maximum: int = 1_024) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be a non-empty string of at most {maximum} characters")
    return value


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value
