from __future__ import annotations

from uuid import uuid4

import pytest

pytest.importorskip("aiortc")

from fastapi.testclient import TestClient
from govor_gateway_security import PairingAuthority
from govor_media.app import create_media_app
from starlette.websockets import WebSocketDisconnect

TOKEN = "test-only-pairing-token-32-characters"  # noqa: S105


def message(message_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "message_type": message_type,
        "correlation_id": str(uuid4()),
        "payload": payload,
    }


def test_short_pairing_token_is_rejected_at_startup() -> None:
    with pytest.raises(ValueError, match="32 characters"):
        create_media_app(pairing_token="short")  # noqa: S106


def test_unknown_media_source_is_rejected_at_startup() -> None:
    with pytest.raises(ValueError, match="Unsupported media source"):
        create_media_app(pairing_token=TOKEN, media_source="unknown")  # type: ignore[arg-type]


def test_valid_token_is_acknowledged_before_negotiation() -> None:
    with TestClient(create_media_app(pairing_token=TOKEN)).websocket_connect(
        "/v1/media/signaling"
    ) as socket:
        socket.send_json(message("auth.request", {"token": TOKEN}))
        response = socket.receive_json()

    assert response["message_type"] == "auth.ok"


def test_health_identifies_diagnostic_source() -> None:
    with TestClient(create_media_app(pairing_token=TOKEN)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["sources"] == ["diagnostic_video", "diagnostic_audio"]
    assert response.json()["ice_fixture"] is False


def test_invalid_token_closes_with_policy_violation() -> None:
    with TestClient(create_media_app(pairing_token=TOKEN)).websocket_connect(
        "/v1/media/signaling"
    ) as socket:
        socket.send_json(message("auth.request", {"token": "x" * 32}))
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()


def test_release_device_credential_is_accepted(tmp_path) -> None:
    store = tmp_path / "gateway.json"
    authority = PairingAuthority(store)
    code, _ = authority.create_pairing_code()
    device_id = str(uuid4())
    credential = authority.exchange_code(
        code=code,
        device_id=device_id,
        device_name="Test phone",
        client_id="testclient",
    )

    app = create_media_app(gateway_credentials_file=str(store))
    with TestClient(app).websocket_connect("/v1/media/signaling") as socket:
        socket.send_json(
            message(
                "auth.request",
                {"device_id": device_id, "credential": credential},
            )
        )
        response = socket.receive_json()

    assert response["message_type"] == "auth.ok"


def test_media_auth_configuration_is_unambiguous(tmp_path) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        create_media_app()
    with pytest.raises(ValueError, match="exactly one"):
        create_media_app(pairing_token=TOKEN, gateway_credentials_file=str(tmp_path / "x"))
    with pytest.raises(ValueError, match="both test-only ICE fixture values"):
        create_media_app(pairing_token=TOKEN, ice_fixture_advertise_host="10.0.2.2")
    with pytest.raises(ValueError, match="private or loopback"):
        create_media_app(
            pairing_token=TOKEN,
            ice_fixture_advertise_host="8.8.8.8",
            ice_fixture_bind_port=18770,
        )
