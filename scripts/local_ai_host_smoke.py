"""Exercise real local STT/dialogue through the host orchestration boundary."""

from __future__ import annotations

import argparse
import io
import json
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from govor_contracts import RendererCommandPayload
from govor_host.app import create_app
from govor_host.config import Settings
from govor_provider_interfaces import UtteranceAudio


@dataclass
class SmokeRenderer:
    connected: bool = True
    actions: list[str] = field(default_factory=list)

    async def dispatch(self, payload: RendererCommandPayload, correlation_id: Any) -> None:
        _ = correlation_id
        self.actions.append(payload.action)


class FixtureMicrophoneSource:
    def __init__(self, fixtures: list[bytes]) -> None:
        self._fixtures = fixtures
        self._active: UUID | None = None

    async def begin(self, utterance_id: UUID) -> None:
        if self._active is not None:
            raise RuntimeError("overlapping fixture capture")
        self._active = utterance_id

    async def finish(self, utterance_id: UUID, duration_us: int) -> UtteranceAudio:
        if self._active != utterance_id:
            raise RuntimeError("fixture capture identifier mismatch")
        self._active = None
        wav = self._fixtures.pop(0)
        return UtteranceAudio(utterance_id, duration_us, wav)

    async def cancel(self, utterance_id: UUID | None = None) -> None:
        _ = utterance_id
        self._active = None


def envelope(message_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "message_type": message_type,
        "correlation_id": str(uuid4()),
        "payload": payload,
    }


def duration_us(wav: bytes) -> int:
    with wave.open(io.BytesIO(wav), "rb") as stream:
        return stream.getnframes() * 1_000_000 // stream.getframerate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--whisper-executable", required=True)
    parser.add_argument("--whisper-model", required=True)
    parser.add_argument("--bulgarian-fixture", required=True)
    parser.add_argument("--english-fixture", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    fixture_paths = [Path(arguments.bulgarian_fixture), Path(arguments.english_fixture)]
    fixtures = [path.read_bytes() for path in fixture_paths]
    fixture_durations = [duration_us(wav) for wav in fixtures]
    microphone = FixtureMicrophoneSource(fixtures.copy())
    renderer = SmokeRenderer()
    app = create_app(
        Settings(
            mode="local",
            provider_timeout_seconds=60.0,
            whisper_executable=arguments.whisper_executable,
            whisper_model=arguments.whisper_model,
        ),
        microphone=microphone,
        renderer=renderer,
    )
    turns: list[dict[str, object]] = []
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("session.start", {"client_id": str(uuid4())}))
        ready = socket.receive_json()
        first_turn = socket.receive_json()
        session_id = first_turn["payload"]["session_id"]
        active_turn_id = first_turn["payload"]["turn_id"]
        if ready["payload"]["state"] != "ready":
            raise RuntimeError("host did not enter ready state")

        for expected_language, fixture_duration in zip(
            ("bg", "en"), fixture_durations, strict=True
        ):
            socket.send_json(
                envelope(
                    "teacher.playback_completed",
                    {"session_id": session_id, "turn_id": active_turn_id},
                )
            )
            awaiting = socket.receive_json()
            if awaiting["payload"]["state"] != "awaiting_learner":
                raise RuntimeError("host did not await learner")
            utterance_id = str(uuid4())
            socket.send_json(
                envelope(
                    "learner.recording_started",
                    {"session_id": session_id, "utterance_id": utterance_id},
                )
            )
            if socket.receive_json()["payload"]["state"] != "recording":
                raise RuntimeError("host did not enter recording state")
            socket.send_json(
                envelope(
                    "learner.recording_submitted",
                    {
                        "session_id": session_id,
                        "utterance_id": utterance_id,
                        "duration_us": fixture_duration,
                        "audio_reference": "webrtc",
                    },
                )
            )
            if socket.receive_json()["payload"]["state"] != "processing":
                raise RuntimeError("host did not enter processing state")
            transcript = socket.receive_json()
            teacher_turn = socket.receive_json()
            if transcript["message_type"] != "learner.transcript":
                raise RuntimeError("host did not emit a transcript")
            if teacher_turn["message_type"] != "teacher.turn":
                raise RuntimeError("host did not emit a teacher turn")
            if not transcript["payload"]["locale"].startswith(expected_language):
                raise RuntimeError("host transcript language did not match the fixture")
            turns.append(
                {
                    "transcript_provider": transcript["payload"]["provider_id"],
                    "transcript_locale": transcript["payload"]["locale"],
                    "teacher_provider": teacher_turn["payload"]["provider_id"],
                    "teacher_locale": teacher_turn["payload"]["locale"],
                }
            )
            active_turn_id = teacher_turn["payload"]["turn_id"]

        socket.send_json(envelope("session.cancel", {"session_id": session_id, "reason": "user"}))
        socket.receive_json()
        socket.receive_json()

    result = {
        "passed": True,
        "turns": turns,
        "renderer_actions": renderer.actions,
        "retained_recordings": 0,
        "active_sessions_after_close": app.state.session_registry.active_count,
    }
    Path(arguments.output).write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
