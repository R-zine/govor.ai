from __future__ import annotations

import asyncio
import contextlib
import ipaddress
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from govor_contracts import (
    DeviceAuthPayload,
    LessonCatalogProgressPayload,
    MessageEnvelope,
    PairingRequestPayload,
)
from govor_domain import LessonCatalog, load_lesson_catalog
from govor_gateway_security import PairingAuthority, PairingRejected
from govor_progress import SQLiteProgressRepository
from govor_scene_planner import ScenePlanner
from pydantic import ValidationError

from .config import Settings, get_settings
from .environment_catalog_registry import EnvironmentCatalogRegistry
from .fake_lesson import FakeLessonService
from .lesson_catalog_registry import LessonCatalogRegistry
from .microphone import MediaMicrophoneSource, MicrophoneAudioSource, ReferenceOnlyMicrophoneSource
from .orchestration import ControlSession, LessonService, SessionRegistry
from .renderer_gateway import RendererControl, RendererGateway
from .teacher_profiles import TeacherProfileSelection


def create_app(
    settings: Settings | None = None,
    *,
    lesson: LessonService | None = None,
    lesson_catalog: LessonCatalog | None = None,
    microphone: MicrophoneAudioSource | None = None,
    renderer: RendererControl | None = None,
    progress_repository: SQLiteProgressRepository | None = None,
) -> FastAPI:
    runtime = settings or get_settings()
    catalog = lesson_catalog or load_lesson_catalog(runtime.lesson_directory)
    scene_planner = ScenePlanner(runtime.environment_directory)
    for definition in catalog.lessons:
        scene_planner.plan(definition.scene_template_id)
    environment_registry = EnvironmentCatalogRegistry(
        runtime.environment_directory,
        scene_planner,
    )
    catalog_registry = LessonCatalogRegistry(
        runtime.lesson_directory,
        catalog,
        reload_enabled=lesson_catalog is None,
        scene_planner_provider=lambda: environment_registry.planner,
    )
    control_sessions: set[ControlSession] = set()
    teacher_profiles = TeacherProfileSelection()
    progress_store = progress_repository or (
        SQLiteProgressRepository(runtime.progress_database) if runtime.mode == "local" else None
    )

    def lesson_progress(catalog_snapshot: LessonCatalog) -> dict[str, LessonCatalogProgressPayload]:
        exercise_counts = {
            lesson_definition.scenario_id: len(lesson_definition.exercises)
            for lesson_definition in catalog_snapshot.lessons
        }
        summaries = (
            progress_store.lesson_summaries(exercise_counts) if progress_store is not None else {}
        )
        return {
            scenario_id: LessonCatalogProgressPayload(
                status=(
                    summaries[scenario_id].status if scenario_id in summaries else "not_started"
                ),
                successful_exercises=(
                    summaries[scenario_id].successful_exercises if scenario_id in summaries else 0
                ),
                exercise_count=exercise_count,
                completed_count=(
                    summaries[scenario_id].completed_count if scenario_id in summaries else 0
                ),
            )
            for scenario_id, exercise_count in exercise_counts.items()
        }

    lesson_factory: Callable[[LessonCatalog], LessonService]
    if lesson is None and runtime.mode == "local":
        from govor_provider_router.factory import build_configured_lesson_service

        lesson_factory = lambda selected_catalog: build_configured_lesson_service(  # noqa: E731
            runtime,
            lesson_catalog=selected_catalog,
            teacher_profile_provider=lambda: teacher_profiles.profile_id,
            progress_repository=progress_store,
        )
    elif lesson is None:
        lesson_factory = lambda selected_catalog: FakeLessonService(  # noqa: E731
            catalog=selected_catalog
        )
    else:
        lesson_factory = lambda selected_catalog: lesson  # noqa: ARG005, E731
    provider_capabilities = lesson_factory(catalog).capabilities
    microphone_source = microphone or (
        MediaMicrophoneSource(
            runtime.media_capture_url,
            tls_ca_file=runtime.media_capture_tls_ca,
        )
        if runtime.mode == "local"
        else ReferenceOnlyMicrophoneSource()
    )
    renderer_gateway = renderer or RendererGateway(
        acknowledgement_timeout_seconds=runtime.renderer_ack_timeout_seconds,
        teacher_profiles=teacher_profiles,
    )
    session_registry = SessionRegistry()
    pairing_authority = (
        PairingAuthority(runtime.gateway_credentials_file)
        if runtime.gateway_credentials_file
        else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async def watch_lesson_catalog() -> None:
            while True:
                await asyncio.sleep(0.5)
                environment_changed = (
                    environment_registry.refresh(catalog_registry.catalog) is not None
                )
                retry_failed_lessons = (
                    environment_changed and catalog_registry.status == "reload_error"
                )
                if catalog_registry.refresh(force=retry_failed_lessons) is None:
                    continue
                results = await asyncio.gather(
                    *(session.send_lesson_catalog_update() for session in tuple(control_sessions)),
                    return_exceptions=True,
                )
                for result in results:
                    if isinstance(result, Exception):
                        # A failed socket send is cleaned up by its connection handler.
                        continue

        watcher = asyncio.create_task(watch_lesson_catalog())
        try:
            yield
        finally:
            watcher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watcher

    app = FastAPI(title="govor.ai host", version="0.2.0", lifespan=lifespan)
    app.state.session_registry = session_registry
    app.state.renderer_gateway = renderer_gateway
    app.state.lesson_catalog_registry = catalog_registry
    app.state.environment_catalog_registry = environment_registry
    app.state.teacher_profiles = teacher_profiles

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "provider_mode": runtime.mode,
            "offline_only": runtime.offline_only,
            "production_ready": runtime.secure_gateway and pairing_authority is not None,
            "network_scope": "loopback" if runtime.bind_host in {"127.0.0.1", "::1"} else "lan",
            "renderer_connected": renderer_gateway.connected,
            "active_sessions": session_registry.active_count,
            "lesson_count": len(catalog_registry.catalog.lessons),
            "lesson_catalog_status": catalog_registry.status,
            "environment_count": len(environment_registry.planner.supported_templates),
            "environment_catalog_status": environment_registry.status,
            "teacher_profile": teacher_profiles.profile_id,
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

    if pairing_authority is not None:

        @app.post("/v1/pairing")
        async def pair_device(request: Request) -> Response:
            if runtime.secure_gateway and request.url.scheme != "https":
                return Response(status_code=400)
            body = await request.body()
            if len(body) > 8_192:
                return Response(status_code=413)
            correlation_id = "00000000-0000-0000-0000-000000000000"
            try:
                message = MessageEnvelope.model_validate_json(body)
                correlation_id = str(message.correlation_id)
                if message.message_type != "pairing.request":
                    raise ValueError("unsupported pairing message")
                payload = PairingRequestPayload.model_validate(message.payload)
                client_id = request.client.host if request.client else "unknown"
                credential = pairing_authority.exchange_code(
                    code=payload.code,
                    device_id=str(payload.device_id),
                    device_name=payload.device_name,
                    client_id=client_id,
                )
            except (ValidationError, ValueError, PairingRejected):
                return Response(
                    content=_gateway_envelope(
                        "error",
                        correlation_id,
                        {
                            "code": "pairing_rejected",
                            "message": "Pairing was rejected.",
                            "retryable": True,
                        },
                    ),
                    status_code=403,
                    media_type="application/json",
                    headers={"Cache-Control": "no-store"},
                )
            return Response(
                content=_gateway_envelope(
                    "pairing.ok",
                    correlation_id,
                    {"device_id": str(payload.device_id), "credential": credential},
                ),
                media_type="application/json",
                headers={"Cache-Control": "no-store"},
            )

    @app.websocket("/v1/control")
    async def control(websocket: WebSocket) -> None:
        await websocket.accept()
        if runtime.secure_gateway and websocket.url.scheme != "wss":
            await websocket.close(code=1008, reason="secure transport required")
            return
        if pairing_authority is not None and not await _authenticate_websocket(
            websocket,
            pairing_authority,
            runtime.max_control_message_bytes,
        ):
            return
        session = ControlSession(
            send_json=websocket.send_json,
            renderer=renderer_gateway,
            lesson_factory=lesson_factory,
            lesson_catalog_provider=lambda: catalog_registry.catalog,
            lesson_progress_provider=lesson_progress,
            scene_planner_provider=lambda: environment_registry.planner,
            microphone=microphone_source,
            settings=runtime,
            registry=session_registry,
        )
        control_sessions.add(session)
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
            control_sessions.discard(session)
            await session.close()

    if isinstance(renderer_gateway, RendererGateway):

        @app.websocket("/v1/renderer/control")
        async def renderer_control(websocket: WebSocket) -> None:
            loopback = runtime.bind_host in {"127.0.0.1", "::1"}
            if not loopback:
                client = websocket.client
                try:
                    loopback = client is not None and ipaddress.ip_address(client.host).is_loopback
                except ValueError:
                    loopback = False
            if not loopback:
                await websocket.close(code=1008, reason="renderer control is loopback-only")
                return
            await renderer_gateway.serve(
                websocket,
                max_message_bytes=runtime.max_control_message_bytes,
            )

    return app


async def _authenticate_websocket(
    websocket: WebSocket,
    authority: PairingAuthority,
    max_message_bytes: int,
) -> bool:
    try:
        raw = await websocket.receive_text()
        if len(raw.encode("utf-8")) > max_message_bytes:
            await websocket.close(code=1009, reason="authentication message too large")
            return False
        message = MessageEnvelope.model_validate_json(raw)
        if message.message_type != "auth.request":
            raise ValueError("authentication required")
        payload = DeviceAuthPayload.model_validate(message.payload)
        if not authority.authenticate(
            device_id=str(payload.device_id),
            credential=payload.credential,
        ):
            raise ValueError("authentication failed")
        await websocket.send_json(
            {
                "protocol_version": "1.0",
                "message_type": "auth.ok",
                "correlation_id": str(message.correlation_id),
                "payload": {},
            }
        )
        return True
    except (ValidationError, ValueError, WebSocketDisconnect):
        await websocket.close(code=1008, reason="authentication failed")
        return False


def _gateway_envelope(message_type: str, correlation_id: str, payload: dict[str, Any]) -> str:
    try:
        normalized = str(UUID(correlation_id))
    except ValueError:
        normalized = "00000000-0000-0000-0000-000000000000"
    import json

    return json.dumps(
        {
            "protocol_version": "1.0",
            "message_type": message_type,
            "correlation_id": normalized,
            "payload": payload,
        }
    )


app = create_app()
