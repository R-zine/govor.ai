"""Provider-neutral types used by host orchestration and local adapters."""

from .models import (
    DialogueProvider,
    DialogueRequest,
    LessonResult,
    NoSpeechRecognized,
    ProviderError,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
    SpeechProvider,
    SpeechRecognizer,
    TeacherTurn,
    Transcript,
    UtteranceAudio,
)

__all__ = [
    "DialogueProvider",
    "DialogueRequest",
    "LessonResult",
    "NoSpeechRecognized",
    "ProviderError",
    "ProviderMalformedOutput",
    "ProviderResourceExhausted",
    "ProviderUnavailable",
    "SpeechProvider",
    "SpeechRecognizer",
    "TeacherTurn",
    "Transcript",
    "UtteranceAudio",
]
