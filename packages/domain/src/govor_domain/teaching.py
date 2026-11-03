"""Deterministic guided-lesson definitions and progression rules.

The language model may assess an answer's meaning. This module enforces help/language
guards, advances one exercise at a time, and decides completion and difficulty changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .conversation import DetectedLanguage, LearnerIntent, LessonContext


class Difficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ExerciseType(StrEnum):
    GUIDED_RESPONSE = "guided_response"
    VOCABULARY = "vocabulary"
    COMPREHENSION = "comprehension"
    ROLE_PLAY = "role_play"


class LessonStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class DifficultyChangeReason(StrEnum):
    REPEATED_DIFFICULTY = "repeated_difficulty"
    CONSISTENT_FIRST_TRY_SUCCESS = "consistent_first_try_success"


@dataclass(frozen=True, slots=True)
class LearnerSettings:
    english_locale: str = "en-GB"
    starting_difficulty: Difficulty = Difficulty.INTERMEDIATE
    spaced_review_enabled: bool = False

    def __post_init__(self) -> None:
        if self.english_locale not in {"en-GB", "en-US"}:
            raise ValueError("English locale must be en-GB or en-US")


@dataclass(frozen=True, slots=True)
class ExampleInteraction:
    teacher: str
    learner: str

    def __post_init__(self) -> None:
        if any(not value or len(value) > 1_024 for value in (self.teacher, self.learner)):
            raise ValueError("example interaction text must be non-empty and bounded")


@dataclass(frozen=True, slots=True)
class CommonMisunderstanding:
    pattern: str
    correction: str
    explanation_bg: str

    def __post_init__(self) -> None:
        if any(
            not value or len(value) > 1_024
            for value in (self.pattern, self.correction, self.explanation_bg)
        ):
            raise ValueError("misunderstanding text must be non-empty and bounded")


@dataclass(frozen=True, slots=True)
class LessonExercise:
    exercise_id: str
    exercise_type: ExerciseType
    goal: str
    expected_intent: str
    prompts: tuple[str, str, str]
    accepted_patterns: tuple[tuple[str, ...], ...]
    target_vocabulary: tuple[str, ...]
    gentle_correction: str
    explanation_bg: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", self.exercise_id):
            raise ValueError("exercise id must be a bounded slug")
        values = (
            self.exercise_id,
            self.goal,
            self.expected_intent,
            self.gentle_correction,
            self.explanation_bg,
            *self.prompts,
        )
        if any(not value or len(value) > 1_024 for value in values):
            raise ValueError("exercise text must be non-empty and bounded")
        if not self.accepted_patterns or any(not pattern for pattern in self.accepted_patterns):
            raise ValueError("exercise requires at least one non-empty accepted pattern")
        if any(
            not value or len(value) > 128 for pattern in self.accepted_patterns for value in pattern
        ):
            raise ValueError("accepted pattern values must be non-empty and bounded")
        for pattern in self.accepted_patterns:
            slot_indexes = [index for index, value in enumerate(pattern) if _SLOT.fullmatch(value)]
            if len(slot_indexes) > 1 or slot_indexes == [0]:
                raise ValueError("an accepted pattern slot must be unique and follow a literal")
        if not self.target_vocabulary or any(
            not value or len(value) > 128 for value in self.target_vocabulary
        ):
            raise ValueError("exercise vocabulary must be non-empty and bounded")

    def prompt_for(self, difficulty: Difficulty) -> str:
        return self.prompts[_DIFFICULTIES.index(difficulty)]

    def accepts(self, text: str) -> bool:
        normalized = _normalize(text)
        return any(_matches_pattern(normalized, pattern) for pattern in self.accepted_patterns)


@dataclass(frozen=True, slots=True)
class LessonDefinition:
    scenario_id: str
    title: str
    description: str
    display_order: int
    scene_template_id: str
    objectives: tuple[str, ...]
    target_vocabulary: tuple[str, ...]
    difficulty_descriptions: tuple[str, str, str]
    examples: tuple[ExampleInteraction, ...]
    common_misunderstandings: tuple[CommonMisunderstanding, ...]
    exercises: tuple[LessonExercise, ...]
    completion_condition: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", self.scenario_id):
            raise ValueError("scenario id must be a bounded slug")
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", self.scene_template_id):
            raise ValueError("scene template id must be a bounded slug")
        if not 0 <= self.display_order <= 9_999:
            raise ValueError("lesson display order must be between 0 and 9999")
        if not self.title or len(self.title) > 128:
            raise ValueError("lesson title must be non-empty and bounded")
        if not self.description or len(self.description) > 512:
            raise ValueError("lesson description must be non-empty and bounded")
        if not self.objectives or not self.target_vocabulary:
            raise ValueError("lesson metadata must not be empty")
        if len(self.difficulty_descriptions) != len(_DIFFICULTIES):
            raise ValueError("lesson requires one description per difficulty")
        if not self.examples or not self.common_misunderstandings or not self.exercises:
            raise ValueError("lesson guidance must not be empty")
        if not self.completion_condition or len(self.completion_condition) > 1_024:
            raise ValueError("lesson completion condition must be non-empty and bounded")
        exercise_ids = {exercise.exercise_id for exercise in self.exercises}
        if len(exercise_ids) != len(self.exercises):
            raise ValueError("exercise ids must be unique within a scenario")


@dataclass(slots=True)
class TeachingState:
    exercise_index: int = 0
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    attempts_on_exercise: int = 0
    consecutive_first_try_successes: int = 0
    successful_exercises: int = 0
    status: LessonStatus = LessonStatus.IN_PROGRESS
    last_difficulty_reason: DifficultyChangeReason | None = None


@dataclass(frozen=True, slots=True)
class LessonProgress:
    scenario_id: str
    scenario_title: str
    exercise_number: int
    exercise_count: int
    successful_exercises: int
    attempts_on_exercise: int
    difficulty: Difficulty
    status: LessonStatus
    resumed: bool
    difficulty_change_reason: DifficultyChangeReason | None = None


@dataclass(frozen=True, slots=True)
class TeachingOutcome:
    reply_text: str
    reply_locale: str
    progress: LessonProgress
    exercise_id: str
    attempt_recorded: bool
    successful: bool | None
    help_requested: bool
    vocabulary: tuple[str, ...]


class TeachingEngine:
    """Pure progression engine with explainable, bounded adaptation."""

    def __init__(
        self,
        lesson: LessonDefinition,
        state: TeachingState | None = None,
        *,
        resumed: bool = False,
        english_locale: str = "en-GB",
    ) -> None:
        if english_locale not in {"en-GB", "en-US"}:
            raise ValueError("English locale must be en-GB or en-US")
        self.lesson = lesson
        self.state = state or TeachingState()
        self.resumed = resumed
        self.english_locale = english_locale
        if not 0 <= self.state.exercise_index <= len(lesson.exercises):
            raise ValueError("restored exercise index is invalid")
        if self.state.status is LessonStatus.COMPLETED:
            if self.state.exercise_index != len(lesson.exercises):
                raise ValueError("completed state must be at the end of the lesson")
        elif self.state.exercise_index >= len(lesson.exercises):
            raise ValueError("active state must reference an exercise")

    @property
    def current_exercise(self) -> LessonExercise:
        index = min(self.state.exercise_index, len(self.lesson.exercises) - 1)
        return self.lesson.exercises[index]

    def context(self) -> LessonContext:
        exercise = self.current_exercise
        return LessonContext(
            scenario_id=self.lesson.scenario_id,
            title=self.lesson.title,
            objective=exercise.goal,
            teacher_prompt=exercise.prompt_for(self.state.difficulty),
            target_vocabulary=exercise.target_vocabulary,
        )

    def initial_prompt(self) -> str:
        prefix = "Welcome back. " if self.resumed else "Welcome. "
        return prefix + self.current_exercise.prompt_for(self.state.difficulty)

    def progress(self) -> LessonProgress:
        return LessonProgress(
            scenario_id=self.lesson.scenario_id,
            scenario_title=self.lesson.title,
            exercise_number=min(self.state.exercise_index + 1, len(self.lesson.exercises)),
            exercise_count=len(self.lesson.exercises),
            successful_exercises=self.state.successful_exercises,
            attempts_on_exercise=self.state.attempts_on_exercise,
            difficulty=self.state.difficulty,
            status=self.state.status,
            resumed=self.resumed,
            difficulty_change_reason=self.state.last_difficulty_reason,
        )

    def evaluate(
        self,
        text: str,
        language: DetectedLanguage,
        intent: LearnerIntent,
        *,
        answer_accepted: bool | None = None,
    ) -> TeachingOutcome:
        if self.state.status is LessonStatus.COMPLETED:
            raise ValueError("the lesson is already complete")
        exercise = self.current_exercise
        self.state.last_difficulty_reason = None

        if intent is not LearnerIntent.ENGLISH_ANSWER or language is not DetectedLanguage.ENGLISH:
            return self._help_outcome(exercise, intent, language)

        self.state.attempts_on_exercise += 1
        # None means no usable model assessment (including deterministic mock mode).
        accepted = exercise.accepts(text) if answer_accepted is None else answer_accepted
        if not accepted:
            if (
                self.state.attempts_on_exercise == 2
                and self.state.difficulty is not Difficulty.BEGINNER
            ):
                self.state.difficulty = _lower(self.state.difficulty)
                self.state.last_difficulty_reason = DifficultyChangeReason.REPEATED_DIFFICULTY
            self.state.consecutive_first_try_successes = 0
            support = ""
            if self.state.attempts_on_exercise >= 2:
                support = f" {exercise.explanation_bg}"
            reply = (
                f"Nice try. {exercise.gentle_correction}{support} "
                f"Please try again. {exercise.prompt_for(self.state.difficulty)}"
            )
            return TeachingOutcome(
                reply_text=reply,
                reply_locale=self.english_locale,
                progress=self.progress(),
                exercise_id=exercise.exercise_id,
                attempt_recorded=True,
                successful=False,
                help_requested=False,
                vocabulary=exercise.target_vocabulary,
            )

        first_try = self.state.attempts_on_exercise == 1
        self.state.successful_exercises += 1
        self.state.consecutive_first_try_successes = (
            self.state.consecutive_first_try_successes + 1 if first_try else 0
        )
        if (
            self.state.consecutive_first_try_successes >= 2
            and self.state.difficulty is not Difficulty.ADVANCED
        ):
            self.state.difficulty = _raise(self.state.difficulty)
            self.state.consecutive_first_try_successes = 0
            self.state.last_difficulty_reason = DifficultyChangeReason.CONSISTENT_FIRST_TRY_SUCCESS

        self.state.exercise_index += 1
        self.state.attempts_on_exercise = 0
        if self.state.exercise_index == len(self.lesson.exercises):
            self.state.status = LessonStatus.COMPLETED
            reply = (
                f"Well done. You completed {self.lesson.title}. "
                "Your structured progress has been saved."
            )
        else:
            reply = "Good job. " + self.current_exercise.prompt_for(self.state.difficulty)
        return TeachingOutcome(
            reply_text=reply,
            reply_locale=self.english_locale,
            progress=self.progress(),
            exercise_id=exercise.exercise_id,
            attempt_recorded=True,
            successful=True,
            help_requested=False,
            vocabulary=exercise.target_vocabulary,
        )

    def no_speech(self) -> TeachingOutcome:
        exercise = self.current_exercise
        return TeachingOutcome(
            reply_text=(
                "Не успях да чуя ясно. Моля, опитайте отново. "
                + exercise.prompt_for(self.state.difficulty)
            ),
            reply_locale="bg-BG",
            progress=self.progress(),
            exercise_id=exercise.exercise_id,
            attempt_recorded=False,
            successful=None,
            help_requested=True,
            vocabulary=(),
        )

    def _help_outcome(
        self,
        exercise: LessonExercise,
        intent: LearnerIntent,
        language: DetectedLanguage,
    ) -> TeachingOutcome:
        if intent is LearnerIntent.REPEAT:
            reply = "Of course. " + exercise.prompt_for(self.state.difficulty)
            locale = self.english_locale
        elif intent is LearnerIntent.SLOWER_SPEECH:
            reply = "Of course. I will say it more slowly. " + exercise.prompt_for(
                self.state.difficulty
            )
            locale = self.english_locale
        else:
            lead = exercise.explanation_bg
            if language in {DetectedLanguage.BULGARIAN, DetectedLanguage.MIXED}:
                lead += " Българският отговор е помощ, не завършен английски отговор."
            reply = f"{lead} Сега опитайте на английски: {exercise.prompts[0]}"
            locale = "bg-BG"
        return TeachingOutcome(
            reply_text=reply,
            reply_locale=locale,
            progress=self.progress(),
            exercise_id=exercise.exercise_id,
            attempt_recorded=False,
            successful=None,
            help_requested=True,
            vocabulary=(),
        )


_DIFFICULTIES = (Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.ADVANCED)


def _lower(value: Difficulty) -> Difficulty:
    return _DIFFICULTIES[max(0, _DIFFICULTIES.index(value) - 1)]


def _raise(value: Difficulty) -> Difficulty:
    return _DIFFICULTIES[min(len(_DIFFICULTIES) - 1, _DIFFICULTIES.index(value) + 1)]


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.casefold().replace("’", "'")))


_SLOT = re.compile(r"^\{[a-z][a-z0-9_]{0,31}\}$")


def _matches_pattern(normalized_text: str, pattern: tuple[str, ...]) -> bool:
    """Match literal fragments plus an optional learner-chosen value.

    A lesson author can place one ``{slot_name}`` marker after a literal fragment when the
    exercise intentionally lets the learner choose the value (for example, a destination). The
    marker requires at least one word after the preceding fragment. Patterns without a marker
    retain the original order-independent literal-fragment behavior.
    """

    slot_indexes = [index for index, value in enumerate(pattern) if _SLOT.fullmatch(value)]
    if not slot_indexes:
        return all(_normalize(required) in normalized_text for required in pattern)
    if len(slot_indexes) != 1:
        return False

    slot_index = slot_indexes[0]
    if slot_index == 0:
        return False
    prefix = " ".join(_normalize(value) for value in pattern[:slot_index])
    suffix = " ".join(_normalize(value) for value in pattern[slot_index + 1 :])
    if not prefix:
        return False
    slot_expression = r"[a-z0-9']+(?: [a-z0-9']+)*"
    if suffix:
        slot_expression += "?"
    expression = rf"(?:^| ){re.escape(prefix)} (?P<slot>{slot_expression})"
    if suffix:
        expression += rf" {re.escape(suffix)}(?: |$)"
    else:
        expression += r"(?: |$)"
    return re.search(expression, normalized_text) is not None
