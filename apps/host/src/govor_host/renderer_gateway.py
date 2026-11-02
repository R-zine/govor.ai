"""Loopback-only, host-owned control connection to the Godot renderer."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from govor_contracts import (
    MessageEnvelope,
    RendererAckPayload,
    RendererCommandPayload,
    RendererReadyPayload,
    RendererTeacherProfileSelectedPayload,
)
from pydantic import ValidationError

from .teacher_profiles import TeacherProfileSelection

LOGGER = logging.getLogger("uvicorn.error")
SendJson = Callable[[dict[str, object]], Awaitable[None]]
SelectionChanged = Callable[[], Awaitable[None]]


class RendererUnavailable(RuntimeError):
    """Raised when a validated renderer command cannot be acknowledged."""


class RendererControl(Protocol):
    @property
    def connected(self) -> bool: ...

    async def dispatch(self, payload: RendererCommandPayload, correlation_id: UUID) -> None: ...

    async def select_teacher_profile(self, profile_id: str, correlation_id: UUID) -> None: ...


class RendererGateway:
    def __init__(
        self,
        *,
        acknowledgement_timeout_seconds: float,
        teacher_profiles: TeacherProfileSelection | None = None,
        on_teacher_profile_selected: SelectionChanged | None = None,
    ) -> None:
        self._acknowledgement_timeout_seconds = acknowledgement_timeout_seconds
        self._send_json: SendJson | None = None
        self._renderer_id: UUID | None = None
        self._pending: dict[UUID, asyncio.Future[bool]] = {}
        self._send_lock = asyncio.Lock()
        self._teacher_profiles = teacher_profiles or TeacherProfileSelection()
        self._on_teacher_profile_selected = on_teacher_profile_selected

    @property
    def connected(self) -> bool:
        return self._send_json is not None

    async def serve(self, websocket: WebSocket, *, max_message_bytes: int) -> None:
        await websocket.accept()
        registered_renderer_id: UUID | None = None
        try:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > max_message_bytes:
                await websocket.close(code=1009, reason="renderer message too large")
                return
            envelope = MessageEnvelope.model_validate_json(raw)
            if envelope.message_type != "renderer.ready":
                raise ValueError("renderer.ready must be the first renderer message")
            ready = RendererReadyPayload.model_validate(envelope.payload)
            if self.connected:
                await websocket.close(code=1013, reason="a renderer is already connected")
                return

            self._send_json = websocket.send_json
            self._renderer_id = ready.renderer_id
            registered_renderer_id = ready.renderer_id
            LOGGER.info("renderer connected renderer_id=%s", ready.renderer_id)
            await websocket.send_json(
                _envelope(
                    "renderer.ack",
                    envelope.correlation_id,
                    {
                        "command_id": str(envelope.correlation_id),
                        "applied": True,
                    },
                )
            )

            while True:
                raw = await websocket.receive_text()
                if len(raw.encode("utf-8")) > max_message_bytes:
                    await websocket.close(code=1009, reason="renderer message too large")
                    return
                await self._handle_renderer_message(raw)
        except WebSocketDisconnect:
            return
        except (ValidationError, ValueError):
            await websocket.close(code=1008, reason="invalid renderer control message")
        finally:
            if registered_renderer_id is not None and self._renderer_id == registered_renderer_id:
                LOGGER.info("renderer disconnected renderer_id=%s", registered_renderer_id)
                self._send_json = None
                self._renderer_id = None
                self._fail_pending("renderer disconnected")

    async def dispatch(self, payload: RendererCommandPayload, correlation_id: UUID) -> None:
        sender = self._send_json
        if sender is None:
            raise RendererUnavailable("Godot renderer is not connected")

        loop = asyncio.get_running_loop()
        acknowledgement = loop.create_future()
        self._pending[payload.command_id] = acknowledgement
        try:
            async with self._send_lock:
                await sender(
                    _envelope(
                        "renderer.command",
                        correlation_id,
                        payload.model_dump(mode="json"),
                    )
                )
            applied = await asyncio.wait_for(
                acknowledgement,
                timeout=self._acknowledgement_timeout_seconds,
            )
            if not applied:
                raise RendererUnavailable("Godot renderer rejected the command")
        except TimeoutError as error:
            raise RendererUnavailable("Godot renderer acknowledgement timed out") from error
        except RuntimeError as error:
            raise RendererUnavailable("Godot renderer connection failed") from error
        finally:
            self._pending.pop(payload.command_id, None)

    async def select_teacher_profile(self, profile_id: str, correlation_id: UUID) -> None:
        """Apply a closed teacher selection to speech state and the connected renderer."""

        self._teacher_profiles.select(profile_id)
        sender = self._send_json
        if sender is None:
            return
        try:
            async with self._send_lock:
                await sender(
                    _envelope(
                        "renderer.teacher_profile_selected",
                        correlation_id,
                        {"profile_id": profile_id},
                    )
                )
        except RuntimeError as error:
            raise RendererUnavailable("Godot renderer connection failed") from error

    async def _handle_renderer_message(self, raw: str) -> None:
        envelope = MessageEnvelope.model_validate_json(raw)
        if envelope.message_type == "renderer.teacher_profile_selected":
            selection = RendererTeacherProfileSelectedPayload.model_validate(envelope.payload)
            self._teacher_profiles.select(selection.profile_id)
            LOGGER.info("teacher profile selected profile_id=%s", selection.profile_id)
            if self._on_teacher_profile_selected is not None:
                await self._on_teacher_profile_selected()
            return
        if envelope.message_type != "renderer.ack":
            raise ValueError("unsupported renderer control message")
        acknowledgement = RendererAckPayload.model_validate(envelope.payload)
        pending = self._pending.get(acknowledgement.command_id)
        if pending is not None and not pending.done():
            pending.set_result(acknowledgement.applied)

    def _fail_pending(self, detail: str) -> None:
        for pending in self._pending.values():
            if not pending.done():
                pending.set_exception(RendererUnavailable(detail))
        self._pending.clear()


def _envelope(
    message_type: str,
    correlation_id: UUID,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "message_type": message_type,
        "correlation_id": str(correlation_id),
        "payload": payload,
    }
