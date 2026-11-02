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


class PairingRequestPayload(StrictModel):
    code: str = Field(pattern=r"^[0-9]{8}$")
    device_id: UUID
    device_name: str = Field(min_length=1, max_length=64)


class PairingOkPayload(StrictModel):
    device_id: UUID
    credential: str = Field(min_length=32, max_length=256)


class DeviceAuthPayload(StrictModel):
    device_id: UUID
    credential: str = Field(min_length=32, max_length=256)


class SessionStartPayload(StrictModel):
    client_id: UUID
    scenario_id: str = Field(
        default="cafe-ordering",
        pattern=r"^[a-z][a-z0-9-]{2,63}$",
        max_length=64,
    )
    english_locale: Literal["en-GB", "en-US"] = "en-GB"
    spaced_review_enabled: bool = False


class LessonCatalogRequestPayload(StrictModel):
    pass


class LessonCatalogProgressPayload(StrictModel):
    status: Literal["not_started", "in_progress", "completed"]
    successful_exercises: int = Field(ge=0, le=64)
    exercise_count: int = Field(ge=1, le=64)
    completed_count: int = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def validate_counts(self) -> LessonCatalogProgressPayload:
        if self.successful_exercises > self.exercise_count:
            raise ValueError("catalog progress exceeds the lesson exercise count")
        if self.status == "not_started" and (
            self.successful_exercises != 0 or self.completed_count != 0
        ):
            raise ValueError("an unstarted lesson cannot contain progress")
        if self.status == "completed" and (
            self.successful_exercises != self.exercise_count or self.completed_count < 1
        ):
            raise ValueError("completed catalog progress is inconsistent")
        return self


class LessonCatalogItemPayload(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$", max_length=64)
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)
    display_order: int = Field(ge=0, le=9_999)
    progress: LessonCatalogProgressPayload


class LessonCatalogPayload(StrictModel):
    default_scenario_id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$", max_length=64)
    lessons: list[LessonCatalogItemPayload] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_catalog(self) -> LessonCatalogPayload:
        scenario_ids = [lesson.scenario_id for lesson in self.lessons]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("lesson catalog scenario IDs must be unique")
        if self.default_scenario_id not in scenario_ids:
            raise ValueError("default lesson must be present in the catalog")
        expected = sorted(
            self.lessons,
            key=lambda item: (item.display_order, item.title, item.scenario_id),
        )
        if self.lessons != expected:
            raise ValueError("lesson catalog must use display order")
        return self


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


class LessonProgressPayload(StrictModel):
    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$", max_length=64)
    scenario_title: str = Field(min_length=1, max_length=128)
    exercise_number: int = Field(ge=1, le=64)
    exercise_count: int = Field(ge=1, le=64)
    successful_exercises: int = Field(ge=0, le=64)
    attempts_on_exercise: int = Field(ge=0, le=100)
    difficulty: Literal["beginner", "intermediate", "advanced"]
    status: Literal["in_progress", "completed"]
    resumed: bool
    difficulty_change_reason: (
        Literal["repeated_difficulty", "consistent_first_try_success"] | None
    ) = None

    @model_validator(mode="after")
    def validate_counts(self) -> LessonProgressPayload:
        if self.exercise_number > self.exercise_count:
            raise ValueError("lesson exercise number exceeds the exercise count")
        if self.successful_exercises > self.exercise_count:
            raise ValueError("successful exercise count exceeds the exercise count")
        if self.status == "completed" and self.successful_exercises != self.exercise_count:
            raise ValueError("completed lesson must contain every successful exercise")
        return self


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
    lesson_progress: LessonProgressPayload | None = None

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


SceneAssetId = Literal[
    "airport-bench",
    "airport-counter",
    "airport-sign",
    "airport-suitcase",
    "cafe-chair",
    "cafe-counter",
    "cafe-cup",
    "cafe-table",
    "home-bookshelf",
    "home-lamp",
    "home-sofa",
    "home-table",
    "market-basket",
    "market-crate",
    "market-shelf",
]


class Vector3Payload(StrictModel):
    x: float = Field(ge=-20.0, le=20.0)
    y: float = Field(ge=-20.0, le=20.0)
    z: float = Field(ge=-20.0, le=20.0)


class PrimitivePayload(StrictModel):
    shape: Literal["box", "cylinder", "sphere"]
    size: Vector3Payload
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")

    @model_validator(mode="after")
    def validate_size(self) -> PrimitivePayload:
        components = (self.size.x, self.size.y, self.size.z)
        if any(not 0.05 <= component <= 20.0 for component in components):
            raise ValueError("primitive size is outside the accepted range")
        if self.shape == "cylinder" and abs(self.size.x - self.size.z) > 0.001:
            raise ValueError("cylinder x and z size must match")
        return self


class SceneObjectPayload(StrictModel):
    instance_id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$", max_length=64)
    asset_id: SceneAssetId | None = None
    primitive: PrimitivePayload | None = None
    position: Vector3Payload
    yaw_degrees: float = Field(ge=-360.0, le=360.0)
    scale: float = Field(ge=0.1, le=5.0)

    @model_validator(mode="after")
    def validate_source(self) -> SceneObjectPayload:
        if (self.asset_id is None) == (self.primitive is None):
            raise ValueError("scene object requires exactly one asset or primitive")
        return self


class SceneSpecificationPayload(StrictModel):
    scene_id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$", max_length=64)
    environment_id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$", max_length=64)
    camera_preset: Literal["counter", "conversation", "wide"]
    lighting_preset: Literal["warm", "daylight", "terminal", "home"]
    transition: Literal["fade", "cut"]
    avatar_position: Vector3Payload
    avatar_yaw_degrees: float = Field(ge=-360.0, le=360.0)
    objects: list[SceneObjectPayload] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_unique_instances(self) -> SceneSpecificationPayload:
        instance_ids = [item.instance_id for item in self.objects]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("scene object instance IDs must be unique")
        return self


class SpeechEnergySamplePayload(StrictModel):
    media_time_us: int = Field(ge=0, le=30_000_000)
    level_milli: int = Field(ge=0, le=1_000)


class VisemeCuePayload(StrictModel):
    viseme: Literal["silence", "closed", "open", "wide", "round", "teeth"]
    start_us: int = Field(ge=0, le=30_000_000)
    end_us: int = Field(ge=1, le=30_000_000)

    @model_validator(mode="after")
    def validate_range(self) -> VisemeCuePayload:
        if self.end_us <= self.start_us:
            raise ValueError("viseme range is invalid")
        return self


class AvatarAnimationPayload(StrictModel):
    duration_us: int = Field(ge=1, le=30_000_000)
    gesture: Literal["speaking"]
    expression: Literal["encouraging"]
    viseme_source: Literal["provider_phoneme_alignment", "none"]
    speech_energy: list[SpeechEnergySamplePayload] = Field(min_length=1, max_length=768)
    visemes: list[VisemeCuePayload] = Field(max_length=2_048)

    @model_validator(mode="after")
    def validate_timeline(self) -> AvatarAnimationPayload:
        energy_times = [sample.media_time_us for sample in self.speech_energy]
        if energy_times != sorted(energy_times) or len(energy_times) != len(set(energy_times)):
            raise ValueError("speech energy times must be ordered and unique")
        if energy_times[-1] > self.duration_us:
            raise ValueError("speech energy exceeds animation duration")
        previous_end = 0
        for cue in self.visemes:
            if cue.start_us < previous_end or cue.end_us > self.duration_us:
                raise ValueError("viseme timeline is overlapping or outside animation duration")
            previous_end = cue.end_us
        if self.viseme_source == "none" and self.visemes:
            raise ValueError("visemes require provider phoneme alignment")
        return self


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
    scene: SceneSpecificationPayload | None = None
    avatar_animation: AvatarAnimationPayload | None = None

    @model_validator(mode="after")
    def validate_visual_payloads(self) -> RendererCommandPayload:
        if self.scene is not None and self.action != "session_started":
            raise ValueError("scene specifications are accepted only when a session starts")
        if self.avatar_animation is not None:
            if self.action != "teacher_speaking":
                raise ValueError("avatar speech animation requires teacher_speaking")
            if self.duration_us != self.avatar_animation.duration_us:
                raise ValueError("avatar animation duration must match renderer command duration")
        return self


class RendererTeacherProfileSelectedPayload(StrictModel):
    profile_id: Literal["elena", "amira", "daniel"]


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
