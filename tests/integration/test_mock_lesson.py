from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from govor_contracts import RendererCommandPayload
from govor_host.app import create_app
from govor_host.config import Settings


@dataclass
class FakeRendererControl:
    connected: bool = True

    async def dispatch(self, payload: RendererCommandPayload, correlation_id: Any) -> None:
        _ = payload, correlation_id


def test_mock_lesson_requires_no_credentials_or_models(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOVOR_MODEL_PATH", raising=False)
    correlation_id = str(uuid4())
    request = {
        "protocol_version": "1.0",
        "message_type": "session.start",
        "correlation_id": correlation_id,
        "payload": {"client_id": str(uuid4())},
    }

    app = create_app(Settings(mode="fake"), renderer=FakeRendererControl())
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(request)
        state = socket.receive_json()
        response = socket.receive_json()

    assert state["payload"]["state"] == "ready"
    assert response["correlation_id"] == correlation_id
    assert response["payload"]["provider_id"].startswith("fake-")
    assert response["payload"]["audio_base64"].startswith("UklGR")
    assert app.state.session_registry.active_count == 0
