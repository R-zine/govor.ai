from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from govor_contracts import RendererCommandPayload
from govor_host.app import create_app
from govor_host.config import Settings
from govor_host.fake_lesson import AudioReference, FakeLessonService
from starlette.websockets import WebSocketDisconnect


@dataclass
class FakeRendererControl:
    commands: list[RendererCommandPayload] = field(default_factory=list)
    connected: bool = True
    failure: bool = False

    async def dispatch(self, payload: RendererCommandPayload, correlation_id: Any) -> None:
        _ = correlation_id
        if self.failure:
            from govor_host.renderer_gateway import RendererUnavailable

            raise RendererUnavailable("injected renderer failure")
        self.commands.append(payload)


class FailingLessonService(FakeLessonService):
    async def respond(self, audio: AudioReference):  # type: ignore[no-untyped-def]
        _ = audio
        raise RuntimeError("injected provider failure")


class SlowLessonService(FakeLessonService):
    async def respond(self, audio: AudioReference):  # type: ignore[no-untyped-def]
        _ = audio
        await asyncio.sleep(60)
        raise AssertionError("cancelled work resumed")


def envelope(message_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "message_type": message_type,
        "correlation_id": str(uuid4()),
        "payload": payload,
    }


def test_health_identifies_fake_mode() -> None:
    response = TestClient(create_app(Settings(mode="fake"), renderer=FakeRendererControl())).get(
        "/health"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "provider_mode": "fake",
        "production_ready": False,
        "network_scope": "loopback",
        "renderer_connected": True,
        "active_sessions": 0,
    }


def test_complete_fake_lesson_turn_cycle(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO", logger="uvicorn.error")
    renderer = FakeRendererControl()
    app = create_app(Settings(mode="fake"), renderer=renderer)
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("session.start", {"client_id": str(uuid4())}))
        ready = socket.receive_json()
        first_turn = socket.receive_json()
        session_id = first_turn["payload"]["session_id"]
        turn_id = first_turn["payload"]["turn_id"]

        socket.send_json(
            envelope(
                "teacher.playback_completed",
                {"session_id": session_id, "turn_id": turn_id},
            )
        )
        awaiting = socket.receive_json()
        utterance_id = str(uuid4())
        socket.send_json(
            envelope(
                "learner.recording_started",
                {"session_id": session_id, "utterance_id": utterance_id},
            )
        )
        recording = socket.receive_json()
        socket.send_json(
            envelope(
                "learner.recording_submitted",
                {
                    "session_id": session_id,
                    "utterance_id": utterance_id,
                    "duration_us": 750_000,
                    "audio_reference": "webrtc",
                },
            )
        )
        processing = socket.receive_json()
        transcript = socket.receive_json()
        second_turn = socket.receive_json()
        socket.send_json(envelope("session.cancel", {"session_id": session_id, "reason": "user"}))
        ending = socket.receive_json()
        ended = socket.receive_json()

    assert ready["payload"]["state"] == "ready"
    assert first_turn["message_type"] == "teacher.turn"
    assert first_turn["payload"]["provider_id"] == "fake-scripted-speech"
    assert awaiting["payload"]["state"] == "awaiting_learner"
    assert recording["payload"]["state"] == "recording"
    assert processing["payload"]["state"] == "processing"
    assert transcript["message_type"] == "learner.transcript"
    assert transcript["payload"]["provider_id"] == "fake-scripted-stt"
    assert second_turn["payload"]["text"] == "Thank you. Would you like coffee or tea?"
    assert ending["payload"]["state"] == "ending"
    assert ended["message_type"] == "session.ended"
    assert app.state.session_registry.active_count == 0
    assert [command.action for command in renderer.commands] == [
        "session_started",
        "teacher_speaking",
        "awaiting_learner",
        "recording",
        "processing",
        "teacher_speaking",
        "reset",
    ]
    assert "correlation_id=" in caplog.text
    assert "I would like coffee" not in caplog.text
    assert "audio_base64" not in caplog.text


def test_invalid_control_message_is_rejected_without_crashing() -> None:
    app = create_app(Settings(), renderer=FakeRendererControl())
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("host.run_arbitrary_code", {}))
        response = socket.receive_json()

    assert response["message_type"] == "error"
    assert response["payload"]["code"] == "invalid_control_message"
    assert response["payload"]["retryable"] is False


def test_provider_failure_becomes_recoverable_error() -> None:
    app = create_app(
        Settings(),
        renderer=FakeRendererControl(),
        lesson=FailingLessonService(),
    )
    with TestClient(app).websocket_connect("/v1/control") as socket:
        session_id, turn_id = start_session(socket)
        utterance_id = enter_recording(socket, session_id, turn_id)
        socket.send_json(
            envelope(
                "learner.recording_submitted",
                {
                    "session_id": session_id,
                    "utterance_id": utterance_id,
                    "duration_us": 500_000,
                    "audio_reference": "webrtc",
                },
            )
        )
        assert socket.receive_json()["payload"]["state"] == "processing"
        assert socket.receive_json()["payload"]["state"] == "recoverable_error"
        failure = socket.receive_json()

    assert failure["message_type"] == "error"
    assert failure["payload"]["code"] == "provider_failed"
    assert failure["payload"]["retryable"] is True
    assert app.state.session_registry.active_count == 0


def test_cancel_interrupts_provider_work_and_cleans_up() -> None:
    app = create_app(
        Settings(provider_timeout_seconds=30),
        renderer=FakeRendererControl(),
        lesson=SlowLessonService(),
    )
    with TestClient(app).websocket_connect("/v1/control") as socket:
        session_id, turn_id = start_session(socket)
        utterance_id = enter_recording(socket, session_id, turn_id)
        socket.send_json(
            envelope(
                "learner.recording_submitted",
                {
                    "session_id": session_id,
                    "utterance_id": utterance_id,
                    "duration_us": 500_000,
                    "audio_reference": "webrtc",
                },
            )
        )
        assert socket.receive_json()["payload"]["state"] == "processing"
        socket.send_json(envelope("session.cancel", {"session_id": session_id, "reason": "user"}))
        assert socket.receive_json()["payload"]["state"] == "ending"
        assert socket.receive_json()["message_type"] == "session.ended"

    assert app.state.session_registry.active_count == 0


def test_repeated_sessions_release_registry_entries() -> None:
    app = create_app(Settings(), renderer=FakeRendererControl())
    with TestClient(app).websocket_connect("/v1/control") as socket:
        for _ in range(20):
            session_id, _ = start_session(socket)
            socket.send_json(
                envelope("session.cancel", {"session_id": session_id, "reason": "user"})
            )
            assert socket.receive_json()["payload"]["state"] == "ending"
            assert socket.receive_json()["message_type"] == "session.ended"

    assert app.state.session_registry.active_count == 0
    assert app.state.session_registry.started_count == 20
    assert app.state.session_registry.ended_count == 20


def test_real_renderer_gateway_routes_validated_commands_and_acknowledgements() -> None:
    app = create_app(Settings(renderer_ack_timeout_seconds=1))
    with (
        TestClient(app) as client,
        client.websocket_connect("/v1/renderer/control") as renderer_socket,
    ):
        renderer_socket.send_json(
            envelope(
                "renderer.ready",
                {
                    "renderer_id": str(uuid4()),
                    "renderer_kind": "godot",
                    "protocol_version": "1.0",
                },
            )
        )
        assert renderer_socket.receive_json()["message_type"] == "renderer.ack"

        with client.websocket_connect("/v1/control") as control_socket:
            control_socket.send_json(envelope("session.start", {"client_id": str(uuid4())}))
            acknowledge_next_renderer_command(renderer_socket, "session_started")
            ready = control_socket.receive_json()
            acknowledge_next_renderer_command(renderer_socket, "teacher_speaking")
            turn = control_socket.receive_json()
            session_id = turn["payload"]["session_id"]

            assert ready["payload"]["state"] == "ready"
            assert turn["message_type"] == "teacher.turn"
            control_socket.send_json(
                envelope(
                    "session.cancel",
                    {"session_id": session_id, "reason": "user"},
                )
            )
            assert control_socket.receive_json()["payload"]["state"] == "ending"
            acknowledge_next_renderer_command(renderer_socket, "reset")
            assert control_socket.receive_json()["message_type"] == "session.ended"

    assert app.state.session_registry.active_count == 0
    assert app.state.renderer_gateway.connected is False


def test_renderer_gateway_rejects_non_ready_first_message() -> None:
    app = create_app(Settings())
    with TestClient(app).websocket_connect("/v1/renderer/control") as socket:
        socket.send_json(envelope("renderer.ack", {"command_id": str(uuid4()), "applied": True}))
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()

    assert closed.value.code == 1008


def test_playback_timeout_is_recoverable() -> None:
    app = create_app(
        Settings(playback_timeout_seconds=0.01),
        renderer=FakeRendererControl(),
    )
    with TestClient(app).websocket_connect("/v1/control") as socket:
        start_session(socket)
        timeout_state = socket.receive_json()
        timeout_error = socket.receive_json()

    assert timeout_state["payload"]["state"] == "recoverable_error"
    assert timeout_error["payload"]["code"] == "playback_timeout"


def test_malformed_audio_contract_is_rejected_without_echoing_input() -> None:
    app = create_app(Settings(), renderer=FakeRendererControl())
    sensitive = "never-echo-this"
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(
            envelope(
                "learner.recording_submitted",
                {"audio_base64": sensitive},
            )
        )
        response = socket.receive_json()

    assert response["payload"]["code"] == "invalid_control_message"
    assert sensitive not in response["payload"]["message"]


def test_out_of_order_event_reports_invalid_transition() -> None:
    app = create_app(Settings(), renderer=FakeRendererControl())
    with TestClient(app).websocket_connect("/v1/control") as socket:
        session_id, _ = start_session(socket)
        socket.send_json(
            envelope(
                "learner.recording_started",
                {"session_id": session_id, "utterance_id": str(uuid4())},
            )
        )
        response = socket.receive_json()

    assert response["message_type"] == "error"
    assert response["payload"]["code"] == "invalid_transition"
    assert response["payload"]["retryable"] is True


def start_session(socket: Any) -> tuple[str, str]:
    socket.send_json(envelope("session.start", {"client_id": str(uuid4())}))
    assert socket.receive_json()["payload"]["state"] == "ready"
    turn = socket.receive_json()
    return turn["payload"]["session_id"], turn["payload"]["turn_id"]


def enter_recording(socket: Any, session_id: str, turn_id: str) -> str:
    socket.send_json(
        envelope(
            "teacher.playback_completed",
            {"session_id": session_id, "turn_id": turn_id},
        )
    )
    assert socket.receive_json()["payload"]["state"] == "awaiting_learner"
    utterance_id = str(uuid4())
    socket.send_json(
        envelope(
            "learner.recording_started",
            {"session_id": session_id, "utterance_id": utterance_id},
        )
    )
    assert socket.receive_json()["payload"]["state"] == "recording"
    return utterance_id


def acknowledge_next_renderer_command(socket: Any, expected_action: str) -> None:
    command = socket.receive_json()
    assert command["message_type"] == "renderer.command"
    assert command["payload"]["action"] == expected_action
    socket.send_json(
        {
            "protocol_version": "1.0",
            "message_type": "renderer.ack",
            "correlation_id": command["correlation_id"],
            "payload": {
                "command_id": command["payload"]["command_id"],
                "applied": True,
            },
        }
    )
