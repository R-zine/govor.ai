from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .config import Settings, get_settings
from .fake_lesson import FakeLessonService
from .microphone import MediaMicrophoneSource, MicrophoneAudioSource, ReferenceOnlyMicrophoneSource
from .orchestration import ControlSession, LessonService, SessionRegistry
from .renderer_gateway import RendererControl, RendererGateway


def create_app(
    settings: Settings | None = None,
    *,
    lesson: LessonService | None = None,
    microphone: MicrophoneAudioSource | None = None,
    renderer: RendererControl | None = None,
) -> FastAPI:
    runtime = settings or get_settings()
    app = FastAPI(title="govor.ai host", version="0.2.0")
    lesson_factory: Callable[[], LessonService]
    if lesson is None and runtime.mode == "local":
        from govor_provider_router.factory import build_configured_lesson_service

        lesson_factory = lambda: build_configured_lesson_service(runtime)  # noqa: E731
    elif lesson is None:
        lesson_factory = FakeLessonService
    else:
        lesson_factory = lambda: lesson  # noqa: E731
    provider_capabilities = lesson_factory().capabilities
    microphone_source = microphone or (
        MediaMicrophoneSource(runtime.media_capture_url)
        if runtime.mode == "local"
        else ReferenceOnlyMicrophoneSource()
    )
    renderer_gateway = renderer or RendererGateway(
        acknowledgement_timeout_seconds=runtime.renderer_ack_timeout_seconds
    )
    registry = SessionRegistry()
    app.state.session_registry = registry
    app.state.renderer_gateway = renderer_gateway

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "provider_mode": runtime.mode,
            "offline_only": runtime.offline_only,
            "production_ready": False,
            "network_scope": "loopback" if runtime.bind_host in {"127.0.0.1", "::1"} else "lan",
            "renderer_connected": renderer_gateway.connected,
            "active_sessions": registry.active_count,
            "providers": [
                {
                    "provider_id": capability.provider_id,
                    "provider_kind": capability.provider_kind,
                    "local": capability.local,
                    "features": sorted(capability.features),
                }
                for capability in provider_capabilities
            ],
        }

    @app.websocket("/v1/control")
    async def control(websocket: WebSocket) -> None:
        await websocket.accept()
        session = ControlSession(
            send_json=websocket.send_json,
            renderer=renderer_gateway,
            lesson=lesson_factory(),
            microphone=microphone_source,
            settings=runtime,
            registry=registry,
        )
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw.encode("utf-8")) > runtime.max_control_message_bytes:
                    await websocket.close(code=1009, reason="control message too large")
                    return
                await session.handle_text(raw)
        except WebSocketDisconnect:
            return
        finally:
            await session.close()

    if isinstance(renderer_gateway, RendererGateway):

        @app.websocket("/v1/renderer/control")
        async def renderer_control(websocket: WebSocket) -> None:
            await renderer_gateway.serve(
                websocket,
                max_message_bytes=runtime.max_control_message_bytes,
            )

    return app


app = create_app()
