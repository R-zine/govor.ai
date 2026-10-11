"""Stable provider interfaces without framework or runtime dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from govor_contracts import ProviderCapabilities
from govor_domain import (
    ConversationTurn,
    DetectedLanguage,
    DialogueDraft,
    LearnerIntent,
    LessonContext,
)


class ProviderError(RuntimeError):
    """Base class for safe provider failure categorization."""


class ProviderUnavailable(ProviderError):
    pass


class ProviderMalformedOutput(ProviderError):
    pass


class ProviderResourceExhausted(ProviderError):
    pass


class NoSpeechRecognized(ProviderError):
    """The recognizer completed successfully but found no usable speech."""


@dataclass(frozen=True, slots=True)
class UtteranceAudio:
    utterance_id: UUID
    duration_us: int
    wav_bytes: bytes | None

    def __post_init__(self) -> None:
        if not 1 <= self.duration_us <= 30_000_000:
            raise ValueError("utterance duration is outside the accepted range")
        if self.wav_bytes is not None:
            if not 44 <= len(self.wav_bytes) <= 1_000_044:
                raise ValueError("utterance WAV is outside the accepted size range")
            if self.wav_bytes[:4] != b"RIFF" or self.wav_bytes[8:12] != b"WAVE":
                raise ValueError("utterance audio must be a WAV file")


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    locale: str
    language: DetectedLanguage
    provider_id: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class DialogueRequest:
    transcript: Transcript
    lesson: LessonContext
    history: tuple[ConversationTurn, ...]
    intent_hint: LearnerIntent | None


@dataclass(frozen=True, slots=True)
class TeacherTurn:
    text: str
    locale: str
    audio_wav: bytes
    duration_us: int
    provider_id: str


@dataclass(frozen=True, slots=True)
class LessonResult:
    transcript: Transcript | None
    turn: TeacherTurn


class SpeechRecognizer(Protocol):
    capabilities: ProviderCapabilities

    async def transcribe(self, audio: UtteranceAudio) -> Transcript: ...


class DialogueProvider(Protocol):
    capabilities: ProviderCapabilities

    async def generate(self, request: DialogueRequest) -> DialogueDraft: ...


class SpeechProvider(Protocol):
    capabilities: ProviderCapabilities

    async def synthesize(self, text: str, locale: str) -> TeacherTurn: ...
