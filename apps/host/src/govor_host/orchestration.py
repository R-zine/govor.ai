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
    LearnerTranscriptPayload,
    MessageEnvelope,
    ProviderCapabilities,
    RecordingStartedPayload,
    RecordingSubmittedPayload,
    RendererAction,
    RendererCommandPayload,
    SessionCancelPayload,
    SessionEndedPayload,
    SessionErrorPayload,
    SessionScopedPayload,
    SessionStartPayload,
    SessionStatePayload,
    TeacherPlaybackCompletedPayload,
    TeacherTurnPayload,
)
from govor_domain import InvalidTransition, SessionEvent, SessionMachine, SessionState
from govor_provider_interfaces import LessonResult, TeacherTurn, UtteranceAudio
from pydantic import BaseModel, ValidationError

from .config import Settings
from .microphone import MicrophoneAudioSource
from .renderer_gateway import RendererControl, RendererUnavailable

LOGGER = logging.getLogger("uvicorn.error")
SendJson = Callable[[dict[str, object]], Awaitable[None]]


class LessonService(Protocol):
    @property
    def capabilities(self) -> tuple[ProviderCapabilities, ...]: ...

    async def initial_turn(self) -> TeacherTurn: ...

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
    "session.start": SessionStartPayload,
    "teacher.playback_completed": TeacherPlaybackCompletedPayload,
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
        lesson: LessonService,
        microphone: MicrophoneAudioSource,
        settings: Settings,
        registry: SessionRegistry,
    ) -> None:
        self._send_json = send_json
        self._renderer = renderer
        self._lesson = lesson
        self._microphone = microphone
        self._settings = settings
        self._registry = registry
        self._send_lock = asyncio.Lock()
        self._machine = SessionMachine()
        self._session_id: UUID | None = None
        self._client_id: UUID | None = None
        self._turn_id: UUID | None = None
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

    async def _dispatch(self, envelope: MessageEnvelope, payload: BaseModel) -> None:
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

        self._machine = SessionMachine()
        self._session_id = uuid4()
        self._client_id = payload.client_id
        self._registry.start(self._session_id)
        for event in (
            SessionEvent.DISCOVERY_STARTED,
            SessionEvent.HOST_FOUND,
            SessionEvent.PAIRING_ACCEPTED,
        ):
            self._machine.apply(event, uuid4())
        self._machine.apply(SessionEvent.CONNECTED, correlation_id)
        await self._renderer_command("session_started", correlation_id)
        await self._send_state(correlation_id)
        self._start_work(self._prepare_initial_turn(correlation_id))

    async def _prepare_initial_turn(self, correlation_id: UUID) -> None:
        try:
            async with asyncio.timeout(self._settings.provider_timeout_seconds):
                turn = await self._lesson.initial_turn()
            await self._issue_teacher_turn(turn, correlation_id, response=False)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._recoverable_failure(
                correlation_id,
                code=_operation_error_code(error),
                message="The lesson provider did not produce a turn.",
            )

    async def _playback_completed(
        self,
        correlation_id: UUID,
        payload: TeacherPlaybackCompletedPayload,
    ) -> None:
        if payload.turn_id != self._turn_id:
            raise ValueError("turn_id does not match the active turn")
        self._cancel_deadline()
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
                result = await self._lesson.respond(audio)
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
        await self._renderer_command(
            "teacher_speaking",
            correlation_id,
            duration_us=turn.duration_us,
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
                sample_rate_hz=16_000,
                duration_us=turn.duration_us,
                audio_base64=base64.b64encode(turn.audio_wav).decode("ascii"),
                word_alignment=None,
                phoneme_alignment=None,
            ),
        )
        self._arm_deadline(
            self._settings.playback_timeout_seconds,
            expected_state=SessionState.TEACHER_SPEAKING,
            code="playback_timeout",
        )

    async def _retry(self, correlation_id: UUID) -> None:
        self._cancel_deadline()
        self._cancel_work()
        self._machine.apply(SessionEvent.RETRY, correlation_id)
        await self._renderer_command("session_started", correlation_id)
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
        self._utterance_id = None
        self._machine = SessionMachine()

    def _require_session(self, session_id: UUID) -> None:
        if self._session_id is None or self._session_id != session_id:
            raise ValueError("session_id does not match the active session")

    def _require_active_session(self) -> UUID:
        if self._session_id is None:
            raise ValueError("no active session")
        return self._session_id

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
