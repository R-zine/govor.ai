"""Host-owned Milestone 2 session orchestration.

Transport handlers validate and hand messages to this module. It owns lesson state, deadlines,
provider work, renderer dispatch, cancellation, and cleanup; it never logs audio or transcript
content.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, Literal, Protocol, cast
from uuid import UUID, uuid4

from govor_contracts import (
    AvatarAnimationPayload,
    LearnerTranscriptPayload,
    LessonCatalogItemPayload,
    LessonCatalogPayload,
    LessonCatalogRequestPayload,
    LessonProgressPayload,
    MessageEnvelope,
    PhonemeAlignmentPayload,
    PrimitivePayload,
    PronunciationPayload,
    ProviderCapabilities,
    RecordingStartedPayload,
    RecordingSubmittedPayload,
    RendererAction,
    RendererCommandPayload,
    SceneObjectPayload,
    SceneSpecificationPayload,
    SessionCancelPayload,
    SessionEndedPayload,
    SessionErrorPayload,
    SessionScopedPayload,
    SessionStartPayload,
    SessionStatePayload,
    SpeechEnergySamplePayload,
    TeacherPlaybackCompletedPayload,
    TeacherTurnPayload,
    TeacherWordAudioPayload,
    TeacherWordReplayRequestPayload,
    Vector3Payload,
    VisemeCuePayload,
    WordAlignmentPayload,
)
from govor_domain import (
    InvalidTransition,
    LessonCatalog,
    LessonProgress,
    LessonStatus,
    SessionEvent,
    SessionMachine,
    SessionState,
)
from govor_provider_interfaces import LessonResult, TeacherTurn, UtteranceAudio
from govor_scene_planner import (
    ScenePlanner,
    SceneSpecification,
    TimedPhoneme,
    build_avatar_animation,
)
from pydantic import BaseModel, ValidationError

from .config import Settings
from .microphone import MicrophoneAudioSource
from .renderer_gateway import RendererControl, RendererUnavailable

LOGGER = logging.getLogger("uvicorn.error")
SendJson = Callable[[dict[str, object]], Awaitable[None]]


class LessonService(Protocol):
    @property
    def capabilities(self) -> tuple[ProviderCapabilities, ...]: ...

    @property
    def progress(self) -> LessonProgress: ...

    async def initial_turn(
        self,
        scenario_id: str = "cafe-ordering",
        *,
        english_locale: str = "en-GB",
        spaced_review_enabled: bool = False,
    ) -> TeacherTurn: ...

    async def replay_word(self, word: str, locale: str, *, speed: float = 1.0) -> TeacherTurn: ...

    async def respond(self, audio: UtteranceAudio) -> LessonResult: ...


class SessionRegistry:
    """Small observable registry used for health, teardown, and leak checks."""

    def __init__(self) -> None:
        self._active: set[UUID] = set()
        self.started_count = 0
        self.ended_count = 0

    @property
    def active_count(self) -> int:
        return len(self._active)

    def start(self, session_id: UUID) -> None:
        self._active.add(session_id)
        self.started_count += 1

    def end(self, session_id: UUID) -> None:
        if session_id in self._active:
            self._active.remove(session_id)
            self.ended_count += 1


INBOUND_PAYLOADS: dict[str, type[BaseModel]] = {
    "lesson.catalog.request": LessonCatalogRequestPayload,
    "session.start": SessionStartPayload,
    "teacher.playback_completed": TeacherPlaybackCompletedPayload,
    "teacher.word_replay_requested": TeacherWordReplayRequestPayload,
    "learner.recording_started": RecordingStartedPayload,
    "learner.recording_submitted": RecordingSubmittedPayload,
    "session.cancel": SessionCancelPayload,
    "session.retry": SessionScopedPayload,
}


class ControlSession:
    def __init__(
        self,
        *,
        send_json: SendJson,
        renderer: RendererControl,
        lesson_factory: Callable[[LessonCatalog], LessonService],
        lesson_catalog_provider: Callable[[], LessonCatalog],
        microphone: MicrophoneAudioSource,
        settings: Settings,
        registry: SessionRegistry,
        scene_planner_provider: Callable[[], ScenePlanner] = ScenePlanner,
    ) -> None:
        self._send_json = send_json
        self._renderer = renderer
        self._lesson_factory = lesson_factory
        self._lesson_catalog_provider = lesson_catalog_provider
        self._lesson: LessonService | None = None
        self._lesson_catalog: LessonCatalog | None = None
        self._microphone = microphone
        self._settings = settings
        self._registry = registry
        self._scene_planner_provider = scene_planner_provider
        self._send_lock = asyncio.Lock()
        self._machine = SessionMachine()
        self._session_id: UUID | None = None
        self._client_id: UUID | None = None
        self._turn_id: UUID | None = None
        self._active_turn: TeacherTurn | None = None
        self._lesson_completed = False
        self._scenario_id = "cafe-ordering"
        self._english_locale = "en-GB"
        self._spaced_review_enabled = False
        self._utterance_id: UUID | None = None
        self._work_task: asyncio.Task[None] | None = None
        self._deadline_task: asyncio.Task[None] | None = None
        self._closed = False

    @property
    def session_id(self) -> UUID | None:
        return self._session_id

    @property
    def state(self) -> SessionState:
        return self._machine.state

    async def handle_text(self, raw: str) -> None:
        try:
            envelope = MessageEnvelope.model_validate_json(raw)
            payload_type = INBOUND_PAYLOADS.get(envelope.message_type)
            if payload_type is None:
                raise ValueError("unsupported control message type")
            payload = payload_type.model_validate(envelope.payload)
            LOGGER.info(
                "control event=%s correlation_id=%s session_id=%s",
                envelope.message_type,
                envelope.correlation_id,
                self._session_id,
            )
            await self._dispatch(envelope, payload)
        except InvalidTransition:
            await self._send_error(
                _best_effort_correlation_id(raw),
                code="invalid_transition",
                message="The event is not valid in the current session state.",
                retryable=True,
            )
        except (ValidationError, ValueError, json.JSONDecodeError):
            await self._send_error(
                _best_effort_correlation_id(raw),
                code="invalid_control_message",
                message="The control message or payload is invalid.",
                retryable=False,
            )
        except RendererUnavailable:
            await self._recoverable_failure(
                _best_effort_correlation_id(raw),
                code="renderer_unavailable",
                message="The Godot renderer did not apply the session command.",
            )

    async def close(self) -> None:
        self._closed = True
        await self._cleanup_active_session(reason="disconnected", notify=False)

    async def send_lesson_catalog_update(self) -> None:
        """Push the latest catalog after a validated host-side import."""

        await self._send_lesson_catalog(uuid4())

    async def _dispatch(self, envelope: MessageEnvelope, payload: BaseModel) -> None:
        if envelope.message_type == "lesson.catalog.request":
            _require(payload, LessonCatalogRequestPayload)
            await self._send_lesson_catalog(envelope.correlation_id)
            return
        if envelope.message_type == "session.start":
            await self._start(envelope.correlation_id, _require(payload, SessionStartPayload))
            return

        session_payload = _require(payload, SessionScopedPayload)
        self._require_session(session_payload.session_id)
        if envelope.message_type == "teacher.playback_completed":
            await self._playback_completed(
                envelope.correlation_id,
                _require(payload, TeacherPlaybackCompletedPayload),
            )
        elif envelope.message_type == "teacher.word_replay_requested":
            await self._word_replay_requested(
                envelope.correlation_id,
                _require(payload, TeacherWordReplayRequestPayload),
            )
        elif envelope.message_type == "learner.recording_started":
            await self._recording_started(
                envelope.correlation_id,
                _require(payload, RecordingStartedPayload),
            )
        elif envelope.message_type == "learner.recording_submitted":
            await self._recording_submitted(
                envelope.correlation_id,
                _require(payload, RecordingSubmittedPayload),
            )
        elif envelope.message_type == "session.cancel":
            await self._cleanup_active_session(reason="cancelled", notify=True)
        elif envelope.message_type == "session.retry":
            await self._retry(envelope.correlation_id)

    async def _start(self, correlation_id: UUID, payload: SessionStartPayload) -> None:
        if self._session_id is not None:
            await self._send_error(
                correlation_id,
                code="session_already_active",
                message="End the active session before starting another.",
                retryable=False,
            )
            return

        lesson_catalog = self._lesson_catalog_provider()
        lesson_definition = lesson_catalog.get(payload.scenario_id)
        self._lesson_catalog = lesson_catalog
        self._lesson = self._lesson_factory(lesson_catalog)
        self._machine = SessionMachine()
        self._session_id = uuid4()
        self._client_id = payload.client_id
        self._scenario_id = payload.scenario_id
        self._english_locale = payload.english_locale
        self._spaced_review_enabled = payload.spaced_review_enabled
        self._registry.start(self._session_id)
        for event in (
            SessionEvent.DISCOVERY_STARTED,
            SessionEvent.HOST_FOUND,
            SessionEvent.PAIRING_ACCEPTED,
        ):
            self._machine.apply(event, uuid4())
        self._machine.apply(SessionEvent.CONNECTED, correlation_id)
        scene = self._scene_planner_provider().plan(lesson_definition.scene_template_id)
        await self._renderer_command(
            "session_started",
            correlation_id,
            scene=_scene_specification_payload(scene),
        )
        await self._send_state(correlation_id)
        self._start_work(self._prepare_initial_turn(correlation_id))

    async def _prepare_initial_turn(self, correlation_id: UUID) -> None:
        try:
            async with asyncio.timeout(self._settings.provider_timeout_seconds):
                turn = await self._require_lesson().initial_turn(
                    self._scenario_id,
                    english_locale=self._english_locale,
                    spaced_review_enabled=self._spaced_review_enabled,
                )
            await self._issue_teacher_turn(turn, correlation_id, response=False)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._recoverable_failure(
                correlation_id,
                code=_operation_error_code(error),
                message="The lesson provider did not produce a turn.",
            )

    async def _send_lesson_catalog(self, correlation_id: UUID) -> None:
        catalog = self._lesson_catalog_provider()
        await self._send(
            "lesson.catalog",
            correlation_id,
            LessonCatalogPayload(
                default_scenario_id=catalog.default_scenario_id,
                lessons=[
                    LessonCatalogItemPayload(
                        scenario_id=lesson.scenario_id,
                        title=lesson.title,
                        description=lesson.description,
                        display_order=lesson.display_order,
                    )
                    for lesson in catalog.lessons
                ],
            ),
        )

    async def _playback_completed(
        self,
        correlation_id: UUID,
        payload: TeacherPlaybackCompletedPayload,
    ) -> None:
        if payload.turn_id != self._turn_id:
            raise ValueError("turn_id does not match the active turn")
        self._cancel_deadline()
        if self._lesson_completed:
            await self._cleanup_active_session(reason="completed", notify=True)
            return
        self._machine.apply(SessionEvent.TEACHER_PLAYBACK_FINISHED, correlation_id)
        await self._renderer_command("awaiting_learner", correlation_id)
        await self._send_state(correlation_id)
        self._arm_deadline(
            self._settings.recording_timeout_seconds,
            expected_state=SessionState.AWAITING_LEARNER,
            code="learner_response_timeout",
        )

    async def _recording_started(
        self,
        correlation_id: UUID,
        payload: RecordingStartedPayload,
    ) -> None:
        self._cancel_deadline()
        self._machine.apply(SessionEvent.RECORDING_STARTED, correlation_id)
        self._utterance_id = payload.utterance_id
        try:
            async with asyncio.timeout(self._settings.capture_timeout_seconds):
                await self._microphone.begin(payload.utterance_id)
        except Exception as error:
            await self._recoverable_failure(
                correlation_id,
                code=_operation_error_code(error),
                message="Microphone capture could not be started.",
            )
            return
        await self._renderer_command("recording", correlation_id)
        await self._send_state(correlation_id)
        self._arm_deadline(
            self._settings.recording_timeout_seconds,
            expected_state=SessionState.RECORDING,
            code="recording_timeout",
        )

    async def _word_replay_requested(
        self,
        correlation_id: UUID,
        payload: TeacherWordReplayRequestPayload,
    ) -> None:
        if self._machine.state is not SessionState.AWAITING_LEARNER:
            raise InvalidTransition("word replay is only available while awaiting the learner")
        if payload.turn_id != self._turn_id or self._active_turn is None:
            raise ValueError("turn_id does not match the active turn")
        if payload.word_index >= len(self._active_turn.pronunciations):
            raise ValueError("word_index does not exist in the active turn")
        pronunciation = self._active_turn.pronunciations[payload.word_index]
        self._cancel_deadline()
        try:
            async with asyncio.timeout(self._settings.provider_timeout_seconds):
                replay = await self._require_lesson().replay_word(
                    pronunciation.word,
                    pronunciation.locale,
                    speed=payload.playback_rate,
                )
            await self._send(
                "teacher.word_audio",
                correlation_id,
                TeacherWordAudioPayload(
                    session_id=self._require_active_session(),
                    turn_id=payload.turn_id,
                    word_index=payload.word_index,
                    word=pronunciation.word,
                    locale=replay.locale,
                    provider_id=replay.provider_id,
                    sample_rate_hz=replay.sample_rate_hz,
                    duration_us=replay.duration_us,
                    audio_base64=base64.b64encode(replay.audio_wav).decode("ascii"),
                    fallback_used=replay.fallback_used,
                ),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            await self._send_error(
                correlation_id,
                code="word_replay_failed",
                message="The selected word could not be synthesized.",
                retryable=False,
            )
        finally:
            if self._machine.state is SessionState.AWAITING_LEARNER:
                self._arm_deadline(
                    self._settings.recording_timeout_seconds,
                    expected_state=SessionState.AWAITING_LEARNER,
                    code="learner_response_timeout",
                )

    async def _recording_submitted(
        self,
        correlation_id: UUID,
        payload: RecordingSubmittedPayload,
    ) -> None:
        if payload.utterance_id != self._utterance_id:
            raise ValueError("utterance_id does not match the active recording")
        self._cancel_deadline()
        self._machine.apply(SessionEvent.RECORDING_SUBMITTED, correlation_id)
        await self._renderer_command("processing", correlation_id)
        await self._send_state(correlation_id)
        self._start_work(self._complete_response(payload, correlation_id))

    async def _complete_response(
        self,
        payload: RecordingSubmittedPayload,
        correlation_id: UUID,
    ) -> None:
        try:
            async with asyncio.timeout(self._settings.provider_timeout_seconds):
                audio = await self._microphone.finish(
                    payload.utterance_id,
                    payload.duration_us,
                )
                result = await self._require_lesson().respond(audio)
            session_id = self._require_active_session()
            if result.transcript is not None:
                await self._send(
                    "learner.transcript",
                    correlation_id,
                    LearnerTranscriptPayload(
                        session_id=session_id,
                        utterance_id=payload.utterance_id,
                        text=result.transcript.text,
                        locale=result.transcript.locale,
                        provider_id=result.transcript.provider_id,
                    ),
                )
            await self._issue_teacher_turn(result.turn, correlation_id, response=True)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._recoverable_failure(
                correlation_id,
                code=_operation_error_code(error),
                message="The lesson provider could not complete the turn.",
            )

    async def _issue_teacher_turn(
        self,
        turn: TeacherTurn,
        correlation_id: UUID,
        *,
        response: bool,
    ) -> None:
        self._turn_id = uuid4()
        self._active_turn = turn
        progress = self._require_lesson().progress
        self._lesson_completed = progress.status is LessonStatus.COMPLETED
        await self._renderer_command(
            "teacher_speaking",
            correlation_id,
            duration_us=turn.duration_us,
            avatar_animation=_avatar_animation_payload(turn),
        )
        event = SessionEvent.RESPONSE_READY if response else SessionEvent.TEACHER_PLAYBACK_STARTED
        self._machine.apply(event, uuid4())
        session_id = self._require_active_session()
        await self._send(
            "teacher.turn",
            correlation_id,
            TeacherTurnPayload(
                session_id=session_id,
                turn_id=self._turn_id,
                text=turn.text,
                locale=turn.locale,
                provider_id=turn.provider_id,
                sample_rate_hz=turn.sample_rate_hz,
                duration_us=turn.duration_us,
                audio_base64=base64.b64encode(turn.audio_wav).decode("ascii"),
                pronunciations=[
                    PronunciationPayload(
                        word=item.word,
                        start_char=item.start_char,
                        end_char=item.end_char,
                        ipa=item.ipa,
                        locale=item.locale,
                        explanation=item.explanation,
                    )
                    for item in turn.pronunciations
                ],
                word_alignment=(
                    [
                        WordAlignmentPayload(
                            word_index=item.word_index,
                            start_us=item.start_us,
                            end_us=item.end_us,
                        )
                        for item in turn.word_alignment
                    ]
                    if turn.word_alignment is not None
                    else None
                ),
                phoneme_alignment=(
                    [
                        PhonemeAlignmentPayload(
                            word_index=item.word_index,
                            symbol=item.symbol,
                            start_us=item.start_us,
                            end_us=item.end_us,
                        )
                        for item in turn.phoneme_alignment
                    ]
                    if turn.phoneme_alignment is not None
                    else None
                ),
                fallback_used=turn.fallback_used,
                lesson_progress=_lesson_progress_payload(progress),
            ),
        )
        self._arm_deadline(
            max(
                self._settings.playback_timeout_seconds,
                turn.duration_us / 1_000_000 / 0.75 + 2.0,
            ),
            expected_state=SessionState.TEACHER_SPEAKING,
            code="playback_timeout",
        )

    async def _retry(self, correlation_id: UUID) -> None:
        self._cancel_deadline()
        self._cancel_work()
        self._machine.apply(SessionEvent.RETRY, correlation_id)
        await self._renderer_command(
            "session_started",
            correlation_id,
            scene=_scene_specification_payload(
                self._scene_planner_provider().plan(
                    self._require_active_catalog().get(self._scenario_id).scene_template_id
                )
            ),
        )
        await self._send_state(correlation_id)
        self._start_work(self._prepare_initial_turn(correlation_id))

    async def _recoverable_failure(
        self,
        correlation_id: UUID,
        *,
        code: str,
        message: str,
    ) -> None:
        if self._closed or self._session_id is None:
            return
        self._cancel_deadline()
        if self._machine.state is not SessionState.RECOVERABLE_ERROR:
            self._machine.apply(SessionEvent.RECOVERABLE_FAILURE, uuid4())
            await self._send_state(correlation_id)
        await self._send_error(correlation_id, code=code, message=message, retryable=True)

    async def _renderer_command(
        self,
        action: str,
        correlation_id: UUID,
        *,
        duration_us: int | None = None,
        scene: SceneSpecificationPayload | None = None,
        avatar_animation: AvatarAnimationPayload | None = None,
    ) -> None:
        session_id = self._require_active_session()
        try:
            await self._renderer.dispatch(
                RendererCommandPayload(
                    session_id=session_id,
                    command_id=uuid4(),
                    action=cast(RendererAction, action),
                    media_start_us=0,
                    duration_us=duration_us,
                    scene=scene,
                    avatar_animation=avatar_animation,
                ),
                correlation_id,
            )
        except RendererUnavailable:
            if self._settings.renderer_required:
                raise

    async def _send_state(self, correlation_id: UUID) -> None:
        await self._send(
            "session.state",
            correlation_id,
            SessionStatePayload(
                session_id=self._require_active_session(),
                state=self._machine.state.value,
                event_id=correlation_id,
            ),
        )

    async def _send_error(
        self,
        correlation_id: UUID,
        *,
        code: str,
        message: str,
        retryable: bool,
    ) -> None:
        await self._send(
            "error",
            correlation_id,
            SessionErrorPayload(
                code=code,
                message=message,
                retryable=retryable,
                session_id=self._session_id,
            ),
        )

    async def _send(self, message_type: str, correlation_id: UUID, payload: BaseModel) -> None:
        if self._closed:
            return
        envelope: dict[str, object] = {
            "protocol_version": "1.0",
            "message_type": message_type,
            "correlation_id": str(correlation_id),
            "payload": payload.model_dump(mode="json"),
        }
        async with self._send_lock:
            await self._send_json(envelope)

    def _start_work(self, operation: Coroutine[Any, Any, None]) -> None:
        self._cancel_work()
        task: asyncio.Task[None] = asyncio.create_task(operation)
        self._work_task = task
        task.add_done_callback(self._consume_task_result)

    def _arm_deadline(
        self,
        seconds: float,
        *,
        expected_state: SessionState,
        code: str,
    ) -> None:
        self._cancel_deadline()

        async def expire() -> None:
            await asyncio.sleep(seconds)
            if self._machine.state is expected_state:
                await self._recoverable_failure(
                    uuid4(),
                    code=code,
                    message="The session step timed out and can be retried.",
                )

        self._deadline_task = asyncio.create_task(expire())
        self._deadline_task.add_done_callback(self._consume_task_result)

    def _cancel_work(self) -> None:
        task = self._work_task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
        self._work_task = None

    def _cancel_deadline(self) -> None:
        task = self._deadline_task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
        self._deadline_task = None

    async def _cleanup_active_session(self, *, reason: str, notify: bool) -> None:
        session_id = self._session_id
        if session_id is None:
            return
        self._cancel_work()
        self._cancel_deadline()
        await self._microphone.cancel(self._utterance_id)
        correlation_id = uuid4()
        if self._machine.state not in {SessionState.DISCONNECTED, SessionState.ENDING}:
            self._machine.apply(SessionEvent.END_REQUESTED, correlation_id)
            if notify:
                await self._send_state(correlation_id)
        with contextlib.suppress(RendererUnavailable):
            await self._renderer.dispatch(
                RendererCommandPayload(
                    session_id=session_id,
                    command_id=uuid4(),
                    action="reset",
                    media_start_us=0,
                    duration_us=None,
                ),
                correlation_id,
            )
        if self._machine.state is SessionState.ENDING:
            self._machine.apply(SessionEvent.ENDED, uuid4())
        if notify:
            await self._send(
                "session.ended",
                correlation_id,
                SessionEndedPayload(
                    session_id=session_id,
                    reason=cast(Literal["cancelled", "completed", "disconnected"], reason),
                ),
            )
        self._registry.end(session_id)
        self._session_id = None
        self._client_id = None
        self._turn_id = None
        self._active_turn = None
        self._lesson_completed = False
        self._utterance_id = None
        self._lesson = None
        self._lesson_catalog = None
        self._machine = SessionMachine()

    def _require_session(self, session_id: UUID) -> None:
        if self._session_id is None or self._session_id != session_id:
            raise ValueError("session_id does not match the active session")

    def _require_active_session(self) -> UUID:
        if self._session_id is None:
            raise ValueError("no active session")
        return self._session_id

    def _require_lesson(self) -> LessonService:
        if self._lesson is None:
            raise ValueError("no active lesson")
        return self._lesson

    def _require_active_catalog(self) -> LessonCatalog:
        if self._lesson_catalog is None:
            raise ValueError("no active lesson catalog")
        return self._lesson_catalog

    @staticmethod
    def _consume_task_result(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            LOGGER.error("background session task failed error_type=%s", type(error).__name__)


def _require[T: BaseModel](payload: BaseModel, expected_type: type[T]) -> T:
    if not isinstance(payload, expected_type):
        raise TypeError(f"expected {expected_type.__name__}")
    return payload


def _best_effort_correlation_id(raw: str) -> UUID:
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError
        return UUID(str(parsed.get("correlation_id")))
    except (TypeError, ValueError, json.JSONDecodeError):
        return UUID(int=0)


def _operation_error_code(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "provider_timeout"
    if isinstance(error, RendererUnavailable):
        return "renderer_unavailable"
    return "provider_failed"


def _lesson_progress_payload(progress: LessonProgress) -> LessonProgressPayload:
    return LessonProgressPayload(
        scenario_id=progress.scenario_id,
        scenario_title=progress.scenario_title,
        exercise_number=progress.exercise_number,
        exercise_count=progress.exercise_count,
        successful_exercises=progress.successful_exercises,
        attempts_on_exercise=progress.attempts_on_exercise,
        difficulty=progress.difficulty.value,
        status=progress.status.value,
        resumed=progress.resumed,
        difficulty_change_reason=(
            progress.difficulty_change_reason.value
            if progress.difficulty_change_reason is not None
            else None
        ),
    )


def _scene_specification_payload(scene: SceneSpecification) -> SceneSpecificationPayload:
    return SceneSpecificationPayload(
        scene_id=scene.scene_id,
        environment_id=scene.environment_id,
        camera_preset=scene.camera_preset,
        lighting_preset=scene.lighting_preset,
        transition=scene.transition,
        avatar_position=Vector3Payload(
            x=scene.avatar_position[0],
            y=scene.avatar_position[1],
            z=scene.avatar_position[2],
        ),
        avatar_yaw_degrees=scene.avatar_yaw_degrees,
        objects=[
            SceneObjectPayload(
                instance_id=item.instance_id,
                asset_id=item.asset_id,
                primitive=(
                    PrimitivePayload(
                        shape=item.primitive.shape,
                        size=Vector3Payload(
                            x=item.primitive.size[0],
                            y=item.primitive.size[1],
                            z=item.primitive.size[2],
                        ),
                        color=item.primitive.color,
                    )
                    if item.primitive is not None
                    else None
                ),
                position=Vector3Payload(
                    x=item.position[0],
                    y=item.position[1],
                    z=item.position[2],
                ),
                yaw_degrees=item.yaw_degrees,
                scale=item.scale,
            )
            for item in scene.objects
        ],
    )


def _avatar_animation_payload(turn: TeacherTurn) -> AvatarAnimationPayload:
    animation = build_avatar_animation(
        turn.audio_wav,
        turn.duration_us,
        (
            TimedPhoneme(item.symbol, item.start_us, item.end_us)
            for item in turn.phoneme_alignment or ()
        ),
    )
    return AvatarAnimationPayload(
        duration_us=animation.duration_us,
        gesture=animation.gesture,
        expression=animation.expression,
        viseme_source=animation.viseme_source,
        speech_energy=[
            SpeechEnergySamplePayload(
                media_time_us=item.media_time_us,
                level_milli=item.level_milli,
            )
            for item in animation.speech_energy
        ],
        visemes=[
            VisemeCuePayload(
                viseme=item.viseme,
                start_us=item.start_us,
                end_us=item.end_us,
            )
            for item in animation.visemes
        ],
    )
