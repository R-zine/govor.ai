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


class ProviderAuthenticationError(ProviderError):
    """A configured provider rejected or could not obtain its credential."""


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
class Pronunciation:
    word: str
    start_char: int
    end_char: int
    ipa: str
    locale: str
    explanation: str | None = None

    def __post_init__(self) -> None:
        if not self.word or not self.ipa:
            raise ValueError("pronunciation word and IPA must not be empty")
        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError("pronunciation character range is invalid")


@dataclass(frozen=True, slots=True)
class WordAlignment:
    word_index: int
    start_us: int
    end_us: int

    def __post_init__(self) -> None:
        if self.word_index < 0 or self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("word alignment is invalid")


@dataclass(frozen=True, slots=True)
class PhonemeAlignment:
    word_index: int
    symbol: str
    start_us: int
    end_us: int

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("phoneme symbol must not be empty")
        if self.word_index < 0 or self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("phoneme alignment is invalid")


@dataclass(frozen=True, slots=True)
class TeacherTurn:
    text: str
    locale: str
    audio_wav: bytes
    sample_rate_hz: int
    duration_us: int
    provider_id: str
    pronunciations: tuple[Pronunciation, ...] = ()
    word_alignment: tuple[WordAlignment, ...] | None = None
    phoneme_alignment: tuple[PhonemeAlignment, ...] | None = None
    fallback_used: bool = False

    def __post_init__(self) -> None:
        if not self.text or not self.provider_id:
            raise ValueError("teacher turn text and provider must not be empty")
        if self.sample_rate_hz not in {16_000, 22_050, 24_000, 48_000}:
            raise ValueError("teacher turn sample rate is unsupported")
        if not 1 <= self.duration_us <= 30_000_000:
            raise ValueError("teacher turn duration is outside the accepted range")
        if not 44 <= len(self.audio_wav) <= 1_500_044:
            raise ValueError("teacher turn WAV is outside the accepted size range")
        if self.audio_wav[:4] != b"RIFF" or self.audio_wav[8:12] != b"WAVE":
            raise ValueError("teacher turn audio must be a WAV file")
        for pronunciation in self.pronunciations:
            if pronunciation.end_char > len(self.text):
                raise ValueError("pronunciation range exceeds teacher text")
            if self.text[pronunciation.start_char : pronunciation.end_char] != pronunciation.word:
                raise ValueError("pronunciation range does not match teacher text")
        for alignment in self.word_alignment or ():
            if alignment.word_index >= len(self.pronunciations):
                raise ValueError("word alignment references an unknown pronunciation")
            if alignment.end_us > self.duration_us:
                raise ValueError("word alignment exceeds teacher audio")
        for phoneme in self.phoneme_alignment or ():
            if phoneme.word_index >= len(self.pronunciations):
                raise ValueError("phoneme alignment references an unknown pronunciation")
            if phoneme.end_us > self.duration_us:
                raise ValueError("phoneme alignment exceeds teacher audio")


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

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn: ...
