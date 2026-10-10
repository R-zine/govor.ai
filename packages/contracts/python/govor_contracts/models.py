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

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class TeacherTurnPayload(SessionScopedPayload):
    turn_id: UUID
    text: str = Field(min_length=1, max_length=2_048)
    locale: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$", max_length=16)
    provider_id: str = Field(min_length=1, max_length=64)
    audio_format: Literal["wav"] = "wav"
    sample_rate_hz: Literal[16000, 24000, 48000]
    duration_us: int = Field(ge=1, le=30_000_000)
    audio_base64: str = Field(min_length=4, max_length=1_398_104)
    word_alignment: None = None
    phoneme_alignment: None = None

    @field_validator("audio_base64")
    @classmethod
    def validate_audio_base64(cls, value: str) -> str:
        try:
            audio = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("audio_base64 must be valid base64") from error
        if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
            raise ValueError("audio_base64 must contain a WAV file")
        return value


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
