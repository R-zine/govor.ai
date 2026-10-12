"""Deterministic guided-lesson definitions and progression rules.

The language model may help classify a turn, but this module alone decides whether a
learner succeeded, which exercise comes next, and why difficulty changed.
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


@dataclass(frozen=True, slots=True)
class CommonMisunderstanding:
    pattern: str
    correction: str
    explanation_bg: str


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

    def prompt_for(self, difficulty: Difficulty) -> str:
        return self.prompts[_DIFFICULTIES.index(difficulty)]

    def accepts(self, text: str) -> bool:
        normalized = _normalize(text)
        return any(
            all(_normalize(required) in normalized for required in pattern)
            for pattern in self.accepted_patterns
        )


@dataclass(frozen=True, slots=True)
class LessonDefinition:
    scenario_id: str
    title: str
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
        if not self.title or not self.objectives or not self.target_vocabulary:
            raise ValueError("lesson metadata must not be empty")
        if not self.examples or not self.common_misunderstandings or not self.exercises:
            raise ValueError("lesson guidance must not be empty")
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
    ) -> TeachingOutcome:
        if self.state.status is LessonStatus.COMPLETED:
            raise ValueError("the lesson is already complete")
        exercise = self.current_exercise
        self.state.last_difficulty_reason = None

        if intent is not LearnerIntent.ENGLISH_ANSWER or language is not DetectedLanguage.ENGLISH:
            return self._help_outcome(exercise, intent, language)

        self.state.attempts_on_exercise += 1
        if not exercise.accepts(text):
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


SCENARIOS: dict[str, LessonDefinition] = {
    "cafe-ordering": LessonDefinition(
        scenario_id="cafe-ordering",
        title="Ordering at a café",
        objectives=(
            "Make a polite drink order.",
            "Respond to follow-up questions.",
            "Choose between drinking in and takeaway.",
        ),
        target_vocabulary=("would like", "please", "anything else", "for here", "to go"),
        difficulty_descriptions=(
            "Modelled phrases and a named item.",
            "Short service questions with light cues.",
            "Natural role-play with minimal prompting.",
        ),
        examples=(
            ExampleInteraction("What would you like?", "I would like a coffee, please."),
            ExampleInteraction("For here or to go?", "For here, please."),
        ),
        common_misunderstandings=(
            CommonMisunderstanding(
                "I want coffee",
                "Use ‘I would like’ for a gentler request.",
                "‘I would like’ звучи по-учтиво от директното ‘I want’.",
            ),
        ),
        exercises=(
            LessonExercise(
                "order-drink",
                ExerciseType.GUIDED_RESPONSE,
                "Order a drink politely.",
                "order_drink",
                (
                    "Say: I would like a coffee, please.",
                    "What would you like to drink?",
                    "Welcome to the café. May I take your order?",
                ),
                (("would like", "coffee"), ("can i have", "coffee"), ("coffee", "please")),
                ("would like", "coffee", "please"),
                "A polite order needs the item and a courteous request.",
                "Кажете какво искате с учтивата фраза ‘I would like ... please’.",
            ),
            LessonExercise(
                "finish-order",
                ExerciseType.VOCABULARY,
                "Finish an order after a follow-up question.",
                "finish_order",
                (
                    "Say: That is all, thank you.",
                    "Would you like anything else?",
                    "Anything else for you today?",
                ),
                (("that's all",), ("that is all",), ("nothing else",)),
                ("anything else", "that's all", "thank you"),
                "Use a complete phrase to show that the order is finished.",
                "‘That is all’ означава, че не желаете нищо допълнително.",
            ),
            LessonExercise(
                "here-or-go",
                ExerciseType.COMPREHENSION,
                "Understand and answer the dine-in or takeaway question.",
                "choose_service",
                (
                    "Answer: For here, please.",
                    "Is that for here or to go?",
                    "Will you be having that here, or taking it away?",
                ),
                (("for here",), ("to go",), ("take away",), ("takeaway",)),
                ("for here", "to go"),
                "Choose either eating here or taking the order away.",
                "‘For here’ е за консумация на място, а ‘to go’ е за вкъщи.",
            ),
        ),
        completion_condition="Complete all three café exchanges with English production.",
    ),
    "supermarket-shopping": LessonDefinition(
        scenario_id="supermarket-shopping",
        title="Shopping in a supermarket",
        objectives=(
            "Ask where an item is.",
            "Request a quantity.",
            "Respond at the checkout.",
        ),
        target_vocabulary=("where can I find", "a kilo of", "checkout", "bag"),
        difficulty_descriptions=(
            "Named products and complete models.",
            "Short shopping questions.",
            "Natural supermarket role-play.",
        ),
        examples=(
            ExampleInteraction("Can I help you?", "Where can I find the milk?"),
            ExampleInteraction("Would you like a bag?", "Yes, please."),
        ),
        common_misunderstandings=(
            CommonMisunderstanding(
                "Where is milks?",
                "Milk is normally uncountable: say ‘the milk’.",
                "‘Milk’ обикновено е неброимо и не получава окончание -s.",
            ),
        ),
        exercises=(
            LessonExercise(
                "find-milk",
                ExerciseType.GUIDED_RESPONSE,
                "Ask where a product is.",
                "locate_product",
                (
                    "Say: Where can I find the milk?",
                    "Ask me where the milk is.",
                    "You cannot see the dairy section. Ask an employee for help.",
                ),
                (("where", "milk"), ("find", "milk")),
                ("where", "find", "milk"),
                "Make it a clear question and name the product.",
                "Използвайте ‘Where can I find ...?’ за да попитате къде е продуктът.",
            ),
            LessonExercise(
                "buy-apples",
                ExerciseType.VOCABULARY,
                "Request a quantity of produce.",
                "request_quantity",
                (
                    "Say: I would like a kilo of apples, please.",
                    "How many apples would you like?",
                    "Tell the assistant the quantity of apples you need.",
                ),
                (("kilo", "apple"), ("kilogram", "apple")),
                ("kilo", "apples"),
                "Include both the amount and the product.",
                "‘A kilo of apples’ означава един килограм ябълки.",
            ),
            LessonExercise(
                "checkout-bag",
                ExerciseType.COMPREHENSION,
                "Answer a checkout question.",
                "choose_bag",
                (
                    "Answer: Yes, I would like a bag, please.",
                    "Would you like a bag?",
                    "At the checkout I ask whether you need a bag. Respond naturally.",
                ),
                (("yes", "bag"), ("no", "bag"), ("no thank",)),
                ("checkout", "bag"),
                "Say clearly whether you need a bag.",
                "‘Would you like a bag?’ пита дали желаете торбичка.",
            ),
        ),
        completion_condition="Complete all three supermarket exchanges in English.",
    ),
    "airport-travel": LessonDefinition(
        scenario_id="airport-travel",
        title="Traveling through an airport",
        objectives=(
            "State a destination at check-in.",
            "Describe hand luggage.",
            "Understand a boarding-gate direction.",
        ),
        target_vocabulary=("check in", "boarding pass", "hand luggage", "gate"),
        difficulty_descriptions=(
            "Modelled airport phrases.",
            "Common check-in questions.",
            "Natural airport role-play and directions.",
        ),
        examples=(
            ExampleInteraction("Where are you flying today?", "I am flying to London."),
            ExampleInteraction("Do you have hand luggage?", "Yes, I have one small bag."),
        ),
        common_misunderstandings=(
            CommonMisunderstanding(
                "I fly in London",
                "Use ‘fly to’ before a destination.",
                "За посока се използва ‘fly to’, а не ‘fly in’.",
            ),
        ),
        exercises=(
            LessonExercise(
                "state-destination",
                ExerciseType.GUIDED_RESPONSE,
                "State a flight destination.",
                "state_destination",
                (
                    "Say: I am flying to London.",
                    "Where are you flying today?",
                    "Good morning. What is your destination?",
                ),
                (("flying to", "london"), ("flight to", "london"), ("going to", "london")),
                ("flying", "destination", "London"),
                "Use ‘to’ before the destination.",
                "Кажете ‘flying to’ и след това града, към който пътувате.",
            ),
            LessonExercise(
                "hand-luggage",
                ExerciseType.VOCABULARY,
                "Describe cabin baggage.",
                "describe_luggage",
                (
                    "Say: I have one small bag as hand luggage.",
                    "Do you have any hand luggage?",
                    "Tell the check-in agent what you will take into the cabin.",
                ),
                (("hand luggage",), ("carry on",), ("small bag",)),
                ("hand luggage", "small bag"),
                "Name the bag that stays with you in the cabin.",
                "‘Hand luggage’ е багажът, който вземате със себе си в самолета.",
            ),
            LessonExercise(
                "find-gate",
                ExerciseType.COMPREHENSION,
                "Ask for the boarding gate.",
                "locate_gate",
                (
                    "Ask: Where is gate twelve, please?",
                    "Your boarding pass says gate twelve. Ask for directions.",
                    "Boarding starts soon and you cannot find gate twelve. What do you ask?",
                ),
                (("where", "gate"), ("find", "gate")),
                ("boarding pass", "gate"),
                "Ask where the gate is and include its number if you know it.",
                "‘Gate’ е изходът за качване. Попитайте ‘Where is gate ...?’.",
            ),
        ),
        completion_condition="Complete check-in, luggage, and gate tasks in English.",
    ),
    "home-conversation": LessonDefinition(
        scenario_id="home-conversation",
        title="Everyday conversation at home",
        objectives=(
            "Describe a routine.",
            "Make a polite request for help.",
            "Discuss an evening plan.",
        ),
        target_vocabulary=("usually", "could you", "help me", "this evening"),
        difficulty_descriptions=(
            "Modelled home phrases.",
            "Everyday questions with light cues.",
            "Open but goal-directed home conversation.",
        ),
        examples=(
            ExampleInteraction("What do you do in the morning?", "I usually make breakfast."),
            ExampleInteraction("What shall we do this evening?", "Let's watch a film."),
        ),
        common_misunderstandings=(
            CommonMisunderstanding(
                "I usually am make breakfast",
                "Use the simple present: ‘I usually make breakfast.’",
                "След ‘usually’ тук използвайте сегашно просто време без ‘am’.",
            ),
        ),
        exercises=(
            LessonExercise(
                "morning-routine",
                ExerciseType.ROLE_PLAY,
                "Describe one morning habit.",
                "describe_routine",
                (
                    "Say: I usually make breakfast in the morning.",
                    "What do you usually do in the morning?",
                    "Tell me about one part of your normal morning routine.",
                ),
                (("usually", "morning"), ("every morning",), ("in the morning",)),
                ("usually", "morning"),
                "Use the simple present to describe a regular habit.",
                "За навик използвайте сегашно просто време, например ‘I usually make ...’.",
            ),
            LessonExercise(
                "request-help",
                ExerciseType.GUIDED_RESPONSE,
                "Make a polite request at home.",
                "request_help",
                (
                    "Say: Could you help me with dinner, please?",
                    "Ask me politely to help with dinner.",
                    "Dinner is not ready and you need help. What do you say?",
                ),
                (("could you", "help"), ("can you", "help"), ("help me", "please")),
                ("could you", "help me", "dinner"),
                "Use ‘could you’ or ‘can you’ plus the help you need.",
                "‘Could you help me ...?’ е учтива молба за помощ.",
            ),
            LessonExercise(
                "evening-plan",
                ExerciseType.COMPREHENSION,
                "Suggest an evening activity.",
                "suggest_activity",
                (
                    "Say: Let's watch a film this evening.",
                    "What would you like to do this evening?",
                    "We have no plans after dinner. Suggest something we can do together.",
                ),
                (("let's",), ("this evening",), ("we could",), ("i would like",)),
                ("this evening", "let's"),
                "Make one clear suggestion for the evening.",
                "‘Let’s ...’ се използва, когато предлагате общо занимание.",
            ),
        ),
        completion_condition="Complete the routine, request, and planning exchanges in English.",
    ),
}


def get_scenario(scenario_id: str) -> LessonDefinition:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as error:
        raise ValueError("unknown guided scenario") from error
