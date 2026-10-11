"""Pure bilingual conversation policy for the local English teacher."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum


class LearnerIntent(StrEnum):
    ENGLISH_ANSWER = "english_answer"
    BULGARIAN_CLARIFICATION = "bulgarian_clarification"
    BULGARIAN_REFORMULATION = "bulgarian_reformulation"
    REPEAT = "repeat"
    SLOWER_SPEECH = "slower_speech"
    VOCABULARY_EXPLANATION = "vocabulary_explanation"
    AMBIGUOUS = "ambiguous"
    RECOGNITION_ERROR = "recognition_error"


class DetectedLanguage(StrEnum):
    ENGLISH = "en"
    BULGARIAN = "bg"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LessonContext:
    scenario_id: str
    title: str
    objective: str
    teacher_prompt: str
    target_vocabulary: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (self.scenario_id, self.title, self.objective, self.teacher_prompt):
            if not value or len(value) > 1_024:
                raise ValueError("lesson context values must be non-empty and bounded")
        if len(self.target_vocabulary) > 64:
            raise ValueError("target vocabulary is too large")


CAFE_LESSON = LessonContext(
    scenario_id="cafe-ordering-basics",
    title="Ordering at a cafe",
    objective="Practise making a polite drink order in English.",
    teacher_prompt="Welcome. What would you like to order?",
    target_vocabulary=("coffee", "tea", "please", "I would like"),
)


@dataclass(frozen=True, slots=True)
class Recognition:
    text: str
    language: DetectedLanguage
    locale: str
    provider_id: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        if len(self.text) > 2_048:
            raise ValueError("recognition text is too long")
        if not self.provider_id or len(self.provider_id) > 64:
            raise ValueError("recognition provider id is invalid")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("recognition confidence is invalid")


@dataclass(frozen=True, slots=True)
class DialogueDraft:
    intent: LearnerIntent
    reply_text: str
    reply_locale: str
    advance_exercise: bool

    def __post_init__(self) -> None:
        if not self.reply_text or len(self.reply_text) > 2_048:
            raise ValueError("dialogue reply must be non-empty and bounded")
        if self.reply_locale not in {"en-GB", "bg-BG"}:
            raise ValueError("dialogue reply locale is unsupported")


@dataclass(frozen=True, slots=True)
class DialogueDecision:
    intent: LearnerIntent
    reply_text: str
    reply_locale: str
    advance_exercise: bool


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    learner_text: str
    learner_locale: str
    intent: LearnerIntent
    teacher_text: str
    teacher_locale: str

    def __post_init__(self) -> None:
        if not self.learner_text or not self.teacher_text:
            raise ValueError("conversation turns cannot be empty")
        if len(self.learner_text) > 2_048 or len(self.teacher_text) > 2_048:
            raise ValueError("conversation turn is too long")


@dataclass(slots=True)
class ConversationMemory:
    """Bounded, in-memory session history; it is never persisted by this type."""

    max_turns: int = 8
    _turns: deque[ConversationTurn] = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_turns <= 32:
            raise ValueError("conversation memory bound must be between 1 and 32")

    def append(self, turn: ConversationTurn) -> None:
        self._turns.append(turn)
        while len(self._turns) > self.max_turns:
            self._turns.popleft()

    def snapshot(self) -> tuple[ConversationTurn, ...]:
        return tuple(self._turns)

    def clear(self) -> None:
        self._turns.clear()


class DialoguePolicy:
    """Enforces teaching invariants after untrusted model generation."""

    _HELP_INTENTS = frozenset(
        {
            LearnerIntent.BULGARIAN_CLARIFICATION,
            LearnerIntent.BULGARIAN_REFORMULATION,
            LearnerIntent.REPEAT,
            LearnerIntent.SLOWER_SPEECH,
            LearnerIntent.VOCABULARY_EXPLANATION,
            LearnerIntent.AMBIGUOUS,
            LearnerIntent.RECOGNITION_ERROR,
        }
    )

    def apply(self, recognition: Recognition, draft: DialogueDraft) -> DialogueDecision:
        intent = draft.intent
        if not recognition.text.strip():
            return self.fallback(LearnerIntent.RECOGNITION_ERROR)
        if (
            recognition.language is DetectedLanguage.BULGARIAN
            and intent is LearnerIntent.ENGLISH_ANSWER
        ):
            return self.fallback(LearnerIntent.BULGARIAN_REFORMULATION)

        required_locale = {
            LearnerIntent.BULGARIAN_CLARIFICATION: "bg-BG",
            LearnerIntent.BULGARIAN_REFORMULATION: "bg-BG",
            LearnerIntent.VOCABULARY_EXPLANATION: "bg-BG",
            LearnerIntent.REPEAT: "en-GB",
            LearnerIntent.SLOWER_SPEECH: "en-GB",
        }.get(intent)
        if required_locale is not None and draft.reply_locale != required_locale:
            return self.fallback(intent)

        advance = (
            draft.advance_exercise
            and intent is LearnerIntent.ENGLISH_ANSWER
            and recognition.language in {DetectedLanguage.ENGLISH, DetectedLanguage.MIXED}
        )
        if intent in self._HELP_INTENTS:
            advance = False

        return DialogueDecision(
            intent=intent,
            reply_text=draft.reply_text,
            reply_locale=draft.reply_locale,
            advance_exercise=advance,
        )

    @staticmethod
    def fallback(intent: LearnerIntent) -> DialogueDecision:
        replies: dict[LearnerIntent, tuple[str, str]] = {
            LearnerIntent.BULGARIAN_CLARIFICATION: (
                "Разбира се. Кажете какво не е ясно, а после ще продължим на английски.",
                "bg-BG",
            ),
            LearnerIntent.BULGARIAN_REFORMULATION: (
                "Може да кажете: ‘I would like a coffee, please.’ Сега опитайте на английски.",
                "bg-BG",
            ),
            LearnerIntent.REPEAT: ("Of course. What would you like to order?", "en-GB"),
            LearnerIntent.SLOWER_SPEECH: (
                "Of course. What ... would ... you ... like ... to order?",
                "en-GB",
            ),
            LearnerIntent.VOCABULARY_EXPLANATION: (
                "‘Order’ тук означава да поръчате храна или напитка. What would you like?",
                "bg-BG",
            ),
            LearnerIntent.AMBIGUOUS: (
                "I am not sure I understood. Would you like coffee or tea?",
                "en-GB",
            ),
            LearnerIntent.RECOGNITION_ERROR: (
                "Не успях да чуя ясно. Моля, опитайте отново.",
                "bg-BG",
            ),
            LearnerIntent.ENGLISH_ANSWER: (
                "Thank you. Would you like anything else?",
                "en-GB",
            ),
        }
        text, locale = replies[intent]
        return DialogueDecision(
            intent=intent,
            reply_text=text,
            reply_locale=locale,
            advance_exercise=False,
        )


def detect_language(text: str) -> DetectedLanguage:
    """Conservative script-level signal used alongside the recognizer language result."""

    has_cyrillic = any("\u0400" <= character <= "\u04ff" for character in text)
    has_latin = any("a" <= character.lower() <= "z" for character in text)
    if has_cyrillic and has_latin:
        return DetectedLanguage.MIXED
    if has_cyrillic:
        return DetectedLanguage.BULGARIAN
    if has_latin:
        return DetectedLanguage.ENGLISH
    return DetectedLanguage.UNKNOWN


def classify_explicit_intent(text: str, language: DetectedLanguage) -> LearnerIntent | None:
    """Classify high-confidence help phrases; open-ended answers remain model-classified."""

    lowered = text.casefold()
    if any(term in lowered for term in ("repeat", "say that again", "повтори", "пак")):
        return LearnerIntent.REPEAT
    if any(term in lowered for term in ("slower", "slowly", "по-бавно", "бавно")):
        return LearnerIntent.SLOWER_SPEECH
    if any(term in lowered for term in ("what does", "what is the meaning", "означава", "дума")):
        return LearnerIntent.VOCABULARY_EXPLANATION
    if any(term in lowered for term in ("как да кажа", "how do i say")):
        return LearnerIntent.BULGARIAN_REFORMULATION
    if any(term in lowered for term in ("не разбирам", "обясни", "обяснете")):
        return LearnerIntent.BULGARIAN_CLARIFICATION
    if language is DetectedLanguage.UNKNOWN:
        return LearnerIntent.AMBIGUOUS
    return None
