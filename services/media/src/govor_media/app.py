from __future__ import annotations

import hmac
import ipaddress
import json
from typing import Any, Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from govor_contracts import MessageEnvelope
from pydantic import BaseModel, ConfigDict, ValidationError

from .microphone_capture import CaptureConflict, CaptureEmpty, MicrophoneCapture
from .peer import MediaPeer


class CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utterance_id: UUID


class CaptureCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utterance_id: UUID | None = None


def create_media_app(
    *, pairing_token: str, media_source: Literal["diagnostic", "renderer"] = "diagnostic"
) -> FastAPI:
    if len(pairing_token) < 32:
        raise ValueError("The development pairing token must contain at least 32 characters")
    if media_source not in {"diagnostic", "renderer"}:
        raise ValueError(f"Unsupported media source: {media_source}")

    app = FastAPI(title="govor.ai media feasibility peer", version="0.1.0")
    microphone_capture = MicrophoneCapture()
    app.state.microphone_capture = microphone_capture

    def require_loopback(request: Request) -> None:
        client = request.client
        try:
            is_loopback = client is not None and ipaddress.ip_address(client.host).is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback:
            raise HTTPException(status_code=403, detail="microphone capture is loopback-only")

    @app.post("/v1/internal/microphone/start", status_code=204)
    async def start_microphone_capture(payload: CaptureRequest, request: Request) -> Response:
        require_loopback(request)
        try:
            microphone_capture.begin(payload.utterance_id)
        except CaptureConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return Response(status_code=204)

    @app.post("/v1/internal/microphone/finish")
    async def finish_microphone_capture(payload: CaptureRequest, request: Request) -> Response:
        require_loopback(request)
        try:
            wav = microphone_capture.finish(payload.utterance_id)
        except CaptureEmpty as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except CaptureConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return Response(
            content=wav,
            media_type="audio/wav",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/v1/internal/microphone/cancel", status_code=204)
    async def cancel_microphone_capture(
        payload: CaptureCancelRequest, request: Request
    ) -> Response:
        require_loopback(request)
        try:
            microphone_capture.cancel(payload.utterance_id)
        except CaptureConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return Response(status_code=204)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "media-feasibility",
            "production_ready": False,
            "sources": [f"{media_source}_video", f"{media_source}_audio"],
        }

    @app.websocket("/v1/media/signaling")
    async def signaling(websocket: WebSocket) -> None:
        await websocket.accept()
        peer: MediaPeer | None = None
        authenticated = False
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw.encode("utf-8")) > 1_048_576:
                    await websocket.close(code=1009, reason="signaling message too large")
                    return
                message = MessageEnvelope.model_validate_json(raw)
                correlation_id = str(message.correlation_id)

                if not authenticated:
                    supplied = message.payload.get("token")
                    if message.message_type != "auth.request" or not isinstance(supplied, str):
                        await websocket.close(code=1008, reason="authentication required")
                        return
                    if not hmac.compare_digest(pairing_token, supplied):
                        await websocket.close(code=1008, reason="authentication failed")
                        return
                    authenticated = True
                    await websocket.send_json(_envelope("auth.ok", correlation_id, {}))
                    continue

                if message.message_type == "webrtc.offer":
                    sdp = message.payload.get("sdp")
                    if not isinstance(sdp, str):
                        raise ValueError("webrtc.offer payload requires sdp")
                    if peer is not None:
                        await peer.close()
                    peer = MediaPeer(
                        media_source=media_source,
                        microphone_capture=microphone_capture,
                    )
                    answer = await peer.accept_offer(sdp)
                    await websocket.send_json(
                        _envelope("webrtc.answer", correlation_id, {"sdp": answer})
                    )
                elif message.message_type == "webrtc.end":
                    await websocket.close(code=1000, reason="session ended")
                    return
                else:
                    raise ValueError(f"unsupported signaling message: {message.message_type}")
        except WebSocketDisconnect:
            pass
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            await websocket.send_json(
                _envelope(
                    "error",
                    "00000000-0000-0000-0000-000000000000",
                    {"code": "invalid_signaling", "message": str(error)[:512], "retryable": False},
                )
            )
            await websocket.close(code=1008, reason="invalid signaling")
        finally:
            if peer is not None:
                await peer.close()
            microphone_capture.cancel()

    return app


def _envelope(message_type: str, correlation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized_correlation_id = str(UUID(correlation_id))
    except ValueError:
        normalized_correlation_id = "00000000-0000-0000-0000-000000000000"
    return {
        "protocol_version": "1.0",
        "message_type": message_type,
        "correlation_id": normalized_correlation_id,
        "payload": payload,
    }
