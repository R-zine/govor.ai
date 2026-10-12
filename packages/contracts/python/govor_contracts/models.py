"""Version 1 wire models.

Pydantic validates process-boundary input. Domain code should translate these models into its own
types rather than depending on transport details.
"""

from __future__ import annotations

import base64
import binascii
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _validate_wav_base64(value: str) -> str:
    try:
        audio = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("audio_base64 must be valid base64") from error
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise ValueError("audio_base64 must contain a WAV file")
    if len(audio) > 1_500_044:
        raise ValueError("audio_base64 WAV exceeds the accepted size")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionState(StrEnum):
    DISCONNECTED = "disconnected"
    DISCOVERING = "discovering"
    PAIRING = "pairing"
    CONNECTING = "connecting"
    READY = "ready"
    TEACHER_SPEAKING = "teacher_speaking"
    AWAITING_LEARNER = "awaiting_learner"
    RECORDING = "recording"
    PROCESSING = "processing"
    RECONNECTING = "reconnecting"
    RECOVERABLE_ERROR = "recoverable_error"
    FATAL_ERROR = "fatal_error"
    ENDING = "ending"


class MessageEnvelope(StrictModel):
    protocol_version: Literal["1.0"] = "1.0"
    message_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$", max_length=64)
    correlation_id: UUID
    payload: dict[str, Any]


class ErrorPayload(StrictModel):
    code: str = Field(max_length=64)
    message: str = Field(max_length=512)
    retryable: bool


class SessionStartPayload(StrictModel):
    client_id: UUID


class SessionScopedPayload(StrictModel):
    session_id: UUID


class TeacherPlaybackCompletedPayload(SessionScopedPayload):
    turn_id: UUID


class RecordingStartedPayload(SessionScopedPayload):
    utterance_id: UUID


class RecordingSubmittedPayload(RecordingStartedPayload):
    duration_us: int = Field(ge=1, le=30_000_000)
    audio_reference: Literal["webrtc"] = "webrtc"


class SessionCancelPayload(SessionScopedPayload):
    reason: Literal["user", "disconnect", "timeout"] = "user"


class SessionStatePayload(SessionScopedPayload):
    state: SessionState
    event_id: UUID


class SessionEndedPayload(SessionScopedPayload):
    reason: Literal["cancelled", "completed", "disconnected"]


class PronunciationPayload(StrictModel):
    word: str = Field(min_length=1, max_length=128)
    start_char: int = Field(ge=0, le=2_047)
    end_char: int = Field(ge=1, le=2_048)
    ipa: str = Field(min_length=1, max_length=256)
    locale: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$", max_length=16)
    explanation: str | None = Field(default=None, max_length=512)

    @model_validator(mode="after")
    def validate_range(self) -> PronunciationPayload:
        if self.end_char <= self.start_char:
            raise ValueError("pronunciation range is invalid")
        return self


class WordAlignmentPayload(StrictModel):
    word_index: int = Field(ge=0, le=255)
    start_us: int = Field(ge=0, le=30_000_000)
    end_us: int = Field(ge=1, le=30_000_000)

    @model_validator(mode="after")
    def validate_range(self) -> WordAlignmentPayload:
        if self.end_us <= self.start_us:
            raise ValueError("word alignment range is invalid")
        return self


class PhonemeAlignmentPayload(WordAlignmentPayload):
    symbol: str = Field(min_length=1, max_length=16)


class TeacherTurnPayload(SessionScopedPayload):
    turn_id: UUID
    text: str = Field(min_length=1, max_length=2_048)
    locale: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$", max_length=16)
    provider_id: str = Field(min_length=1, max_length=64)
    audio_format: Literal["wav"] = "wav"
    sample_rate_hz: Literal[16000, 22050, 24000, 48000]
    duration_us: int = Field(ge=1, le=30_000_000)
    audio_base64: str = Field(min_length=4, max_length=2_000_060)
    pronunciations: list[PronunciationPayload] = Field(max_length=256)
    word_alignment: list[WordAlignmentPayload] | None = Field(default=None, max_length=256)
    phoneme_alignment: list[PhonemeAlignmentPayload] | None = Field(
        default=None,
        max_length=2_048,
    )
    fallback_used: bool = False

    @field_validator("audio_base64")
    @classmethod
    def validate_audio_base64(cls, value: str) -> str:
        return _validate_wav_base64(value)

    @model_validator(mode="after")
    def validate_speech_metadata(self) -> TeacherTurnPayload:
        for index, pronunciation in enumerate(self.pronunciations):
            if pronunciation.end_char > len(self.text):
                raise ValueError("pronunciation exceeds teacher text")
            if self.text[pronunciation.start_char : pronunciation.end_char] != pronunciation.word:
                raise ValueError(f"pronunciation {index} does not match teacher text")
        for alignment in [*(self.word_alignment or []), *(self.phoneme_alignment or [])]:
            if alignment.word_index >= len(self.pronunciations):
                raise ValueError("alignment references an unknown pronunciation")
            if alignment.end_us > self.duration_us:
                raise ValueError("alignment exceeds teacher audio")
        return self


class TeacherWordReplayRequestPayload(SessionScopedPayload):
    turn_id: UUID
    word_index: int = Field(ge=0, le=255)
    playback_rate: float = Field(ge=0.5, le=2.0)


class TeacherWordAudioPayload(SessionScopedPayload):
    turn_id: UUID
    word_index: int = Field(ge=0, le=255)
    word: str = Field(min_length=1, max_length=128)
    locale: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$", max_length=16)
    provider_id: str = Field(min_length=1, max_length=64)
    audio_format: Literal["wav"] = "wav"
    sample_rate_hz: Literal[16000, 22050, 24000, 48000]
    duration_us: int = Field(ge=1, le=30_000_000)
    audio_base64: str = Field(min_length=4, max_length=2_000_060)
    fallback_used: bool = False

    @field_validator("audio_base64")
    @classmethod
    def validate_audio_base64(cls, value: str) -> str:
        return _validate_wav_base64(value)


class LearnerTranscriptPayload(SessionScopedPayload):
    utterance_id: UUID
    text: str = Field(min_length=1, max_length=2_048)
    locale: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$", max_length=16)
    provider_id: str = Field(min_length=1, max_length=64)


class RendererReadyPayload(StrictModel):
    renderer_id: UUID
    renderer_kind: Literal["godot"] = "godot"
    protocol_version: Literal["1.0"] = "1.0"


RendererAction = Literal[
    "session_started",
    "teacher_speaking",
    "awaiting_learner",
    "recording",
    "processing",
    "reset",
]


class RendererCommandPayload(SessionScopedPayload):
    command_id: UUID
    action: RendererAction
    media_start_us: int = Field(ge=0)
    duration_us: int | None = Field(default=None, ge=1, le=30_000_000)


class RendererAckPayload(StrictModel):
    command_id: UUID
    applied: bool


class SessionErrorPayload(ErrorPayload):
    session_id: UUID | None = None


class ProviderCapabilities(StrictModel):
    provider_id: str
    provider_kind: str
    local: bool
    features: frozenset[str] = frozenset()


class ProviderHealth(StrictModel):
    provider_id: str
    available: bool
    detail: str | None = None


class AudioChunk(StrictModel):
    utterance_id: UUID
    sequence: int = Field(ge=0)
    format: Literal["pcm_s16le", "wav"]
    sample_rate_hz: Literal[16000, 24000, 48000]
    channels: Literal[1] = 1
    end_of_utterance: bool
    audio_base64: str = Field(max_length=1_398_104)
