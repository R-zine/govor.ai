"""Provider-neutral types used by host orchestration and local adapters."""

from .models import (
    DialogueProvider,
    DialogueRequest,
    LessonResult,
    NoSpeechRecognized,
    PhonemeAlignment,
    Pronunciation,
    ProviderError,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
    SpeechProvider,
    SpeechRecognizer,
    TeacherTurn,
    Transcript,
    UtteranceAudio,
    WordAlignment,
)

__all__ = [
    "DialogueProvider",
    "DialogueRequest",
    "LessonResult",
    "NoSpeechRecognized",
    "PhonemeAlignment",
    "Pronunciation",
    "ProviderError",
    "ProviderMalformedOutput",
    "ProviderResourceExhausted",
    "ProviderUnavailable",
    "SpeechProvider",
    "SpeechRecognizer",
    "TeacherTurn",
    "Transcript",
    "UtteranceAudio",
    "WordAlignment",
]
