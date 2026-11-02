from __future__ import annotations

import asyncio
import json
import shutil
import time
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from govor_contracts import RendererCommandPayload
from govor_domain import DetectedLanguage, LearnerIntent, TeachingEngine, import_lesson_bundle
from govor_gateway_security import PairingAuthority
from govor_host.app import create_app
from govor_host.config import Settings
from govor_host.fake_lesson import FakeLessonService
from govor_progress import SQLiteProgressRepository
from govor_provider_interfaces import LessonResult, Pronunciation, TeacherTurn, UtteranceAudio
from govor_provider_router import (
    CloudAccessPolicy,
    InMemoryCredentialStore,
    OpenAiCompatibleSpeechProvider,
)
from govor_scene_planner import ScenePlanner, import_environment_bundle
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
    async def respond(self, audio: UtteranceAudio):  # type: ignore[no-untyped-def]
        _ = audio
        raise RuntimeError("injected provider failure")


class SlowLessonService(FakeLessonService):
    async def respond(self, audio: UtteranceAudio):  # type: ignore[no-untyped-def]
        _ = audio
        await asyncio.sleep(60)
        raise AssertionError("cancelled work resumed")


class NoSpeechLessonService(FakeLessonService):
    async def respond(self, audio: UtteranceAudio) -> LessonResult:
        _ = audio
        turn = await self.speech.synthesize(
            "Please try again.",
            "en-GB",
            frequency_hz=440.0,
        )
        return LessonResult(transcript=None, turn=turn)


class PronunciationLessonService(FakeLessonService):
    def __init__(self) -> None:
        super().__init__()
        self.replays: list[tuple[str, str, float]] = []

    async def initial_turn(
        self,
        scenario_id: str = "cafe-ordering",
        *,
        english_locale: str = "en-GB",
        spaced_review_enabled: bool = False,
    ) -> TeacherTurn:
        turn = await super().initial_turn(
            scenario_id,
            english_locale=english_locale,
            spaced_review_enabled=spaced_review_enabled,
        )
        return replace(
            turn,
            pronunciations=(
                Pronunciation(
                    word="Welcome",
                    start_char=0,
                    end_char=7,
                    ipa="ˈwɛlkəm",
                    locale="en-GB",
                    explanation="Test pronunciation explanation.",
                ),
            ),
        )

    async def replay_word(self, word: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        self.replays.append((word, locale, speed))
        return await super().replay_word(word, locale, speed=speed)


class CompletingLessonService(FakeLessonService):
    async def respond(self, audio: UtteranceAudio) -> LessonResult:
        transcript = await self.recognizer.transcribe(audio)
        answers = (
            transcript.text,
            "That is all, thank you.",
            "For here, please.",
        )
        for answer in answers:
            outcome = self._engine.evaluate(  # noqa: SLF001 - focused test service
                answer,
                DetectedLanguage.ENGLISH,
                LearnerIntent.ENGLISH_ANSWER,
            )
        turn = await self.speech.synthesize(outcome.reply_text, outcome.reply_locale)
        return LessonResult(transcript=transcript, turn=turn)


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
        "offline_only": True,
        "production_ready": False,
        "network_scope": "loopback",
        "renderer_connected": True,
        "active_sessions": 0,
        "lesson_count": 4,
        "lesson_catalog_status": "ready",
        "environment_count": 4,
        "environment_catalog_status": "ready",
        "teacher_profile": "amira",
        "providers": [
            {
                "provider_id": "fake-scripted-stt",
                "provider_kind": "speech_recognition",
                "local": True,
                "features": ["deterministic", "development_only"],
            },
            {
                "provider_id": "fake-scripted-dialogue",
                "provider_kind": "dialogue",
                "local": True,
                "features": ["deterministic", "development_only"],
            },
            {
                "provider_id": "fake-scripted-speech",
                "provider_kind": "speech_synthesis",
                "local": True,
                "features": ["deterministic", "development_only", "wav"],
            },
        ],
    }


def test_control_returns_the_startup_lesson_catalog() -> None:
    app = create_app(Settings(mode="fake"), renderer=FakeRendererControl())

    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("lesson.catalog.request", {}))
        catalog = socket.receive_json()

    assert catalog["message_type"] == "lesson.catalog"
    assert catalog["payload"]["default_scenario_id"] == "cafe-ordering"
    assert [item["scenario_id"] for item in catalog["payload"]["lessons"]] == [
        "cafe-ordering",
        "supermarket-shopping",
        "airport-travel",
        "home-conversation",
    ]
    assert all(
        item["progress"]["status"] == "not_started" for item in catalog["payload"]["lessons"]
    )


def test_control_catalog_includes_persisted_lesson_progress(tmp_path: Path) -> None:
    progress = SQLiteProgressRepository(tmp_path / "progress.sqlite3")
    lesson = FakeLessonService().catalog.get("cafe-ordering")
    state, _ = progress.load_or_start(lesson.scenario_id, len(lesson.exercises))
    engine = TeachingEngine(lesson, state)
    outcome = engine.evaluate(
        "I would like coffee, please.",
        DetectedLanguage.ENGLISH,
        LearnerIntent.ENGLISH_ANSWER,
    )
    progress.record_outcome(outcome, engine.state)
    app = create_app(
        Settings(mode="fake"),
        renderer=FakeRendererControl(),
        progress_repository=progress,
    )

    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("lesson.catalog.request", {}))
        catalog = socket.receive_json()

    cafe = next(
        item for item in catalog["payload"]["lessons"] if item["scenario_id"] == "cafe-ordering"
    )
    assert cafe["progress"] == {
        "status": "in_progress",
        "successful_exercises": 1,
        "exercise_count": 3,
        "completed_count": 0,
    }


def test_external_lesson_is_advertised_and_startable(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[3] / "assets" / "lesson-content" / "cafe-ordering.json"
    )
    lesson = json.loads(source.read_text(encoding="utf-8"))
    lesson.update(
        {
            "scenario_id": "hotel-check-in",
            "title": "Checking into a hotel",
            "description": "Practice a hotel check-in using the café scene template.",
            "display_order": 10,
        }
    )
    (tmp_path / "hotel-check-in.json").write_text(
        json.dumps(lesson, ensure_ascii=False),
        encoding="utf-8",
    )
    renderer = FakeRendererControl()
    app = create_app(
        Settings(mode="fake", lesson_directory=str(tmp_path)),
        renderer=renderer,
    )

    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("lesson.catalog.request", {}))
        catalog = socket.receive_json()
        socket.send_json(
            envelope(
                "session.start",
                {
                    "client_id": str(uuid4()),
                    "scenario_id": "hotel-check-in",
                },
            )
        )
        ready = socket.receive_json()
        turn = socket.receive_json()

    assert [item["scenario_id"] for item in catalog["payload"]["lessons"]] == ["hotel-check-in"]
    assert ready["payload"]["state"] == "ready"
    assert turn["payload"]["lesson_progress"]["scenario_id"] == "hotel-check-in"
    assert renderer.commands[0].scene is not None
    assert renderer.commands[0].scene.scene_id == "cafe-ordering-v1"


def test_imported_lesson_is_pushed_and_startable_without_reconnect(tmp_path: Path) -> None:
    source_directory = Path(__file__).resolve().parents[3] / "assets" / "lesson-content"
    lesson_directory = tmp_path / "lessons"
    shutil.copytree(source_directory, lesson_directory)
    source = tmp_path / "hotel.json"
    lesson = json.loads((source_directory / "cafe-ordering.json").read_text(encoding="utf-8"))
    lesson.update(
        {
            "scenario_id": "hotel-check-in",
            "title": "Hotel check-in",
            "display_order": 10,
        }
    )
    source.write_text(json.dumps(lesson), encoding="utf-8")
    renderer = FakeRendererControl()
    app = create_app(
        Settings(mode="fake", lesson_directory=str(lesson_directory)),
        renderer=renderer,
    )

    with (
        TestClient(app) as client,
        client.websocket_connect("/v1/control") as socket,
    ):
        socket.send_json(envelope("lesson.catalog.request", {}))
        initial = socket.receive_json()
        assert len(initial["payload"]["lessons"]) == 4

        import_lesson_bundle(
            source,
            lesson_directory,
            allowed_scene_templates={"cafe", "supermarket", "airport", "home"},
        )
        updated = socket.receive_json()
        assert updated["message_type"] == "lesson.catalog"
        assert updated["payload"]["lessons"][-1]["scenario_id"] == "hotel-check-in"

        socket.send_json(
            envelope(
                "session.start",
                {
                    "client_id": str(uuid4()),
                    "scenario_id": "hotel-check-in",
                },
            )
        )
        ready = socket.receive_json()
        turn = socket.receive_json()

    assert ready["payload"]["state"] == "ready"
    assert turn["payload"]["lesson_progress"]["scenario_id"] == "hotel-check-in"


def test_imported_environment_and_lesson_are_startable_without_host_restart(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    lesson_directory = tmp_path / "lessons"
    environment_directory = tmp_path / "environments"
    shutil.copytree(repository_root / "assets/lesson-content", lesson_directory)
    environment_directory.mkdir()
    bundle = tmp_path / "hotel-environment.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr(
            "hotel.json",
            (
                repository_root / "tests/fixtures/contracts/valid/environment-hotel-lobby.json"
            ).read_bytes(),
        )
    renderer = FakeRendererControl()
    app = create_app(
        Settings(
            mode="fake",
            lesson_directory=str(lesson_directory),
            environment_directory=str(environment_directory),
        ),
        renderer=renderer,
    )

    with TestClient(app) as client, client.websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("lesson.catalog.request", {}))
        socket.receive_json()
        import_environment_bundle(bundle, environment_directory)
        deadline = time.monotonic() + 3
        health = client.get("/health").json()
        while health["environment_count"] != 5 and time.monotonic() < deadline:
            time.sleep(0.1)
            health = client.get("/health").json()
        assert health["environment_catalog_status"] == "ready"
        assert health["environment_count"] == 5

        lesson = json.loads(
            (repository_root / "assets/lesson-content/cafe-ordering.json").read_text(
                encoding="utf-8"
            )
        )
        lesson.update(
            {
                "scenario_id": "hotel-check-in",
                "title": "Hotel check-in",
                "display_order": 10,
                "scene_template_id": "hotel-lobby",
            }
        )
        lesson_source = tmp_path / "hotel-lesson.json"
        lesson_source.write_text(json.dumps(lesson), encoding="utf-8")
        import_lesson_bundle(
            lesson_source,
            lesson_directory,
            allowed_scene_templates=set(ScenePlanner(environment_directory).supported_templates),
        )
        updated = socket.receive_json()
        assert updated["payload"]["lessons"][-1]["scenario_id"] == "hotel-check-in"

        socket.send_json(
            envelope(
                "session.start",
                {"client_id": str(uuid4()), "scenario_id": "hotel-check-in"},
            )
        )
        socket.receive_json()
        socket.receive_json()

    scene = renderer.commands[0].scene
    assert scene is not None
    assert scene.environment_id == "hotel-lobby"
    assert scene.objects[0].primitive is not None


def test_invalid_live_edit_keeps_last_valid_catalog(tmp_path: Path) -> None:
    source_directory = Path(__file__).resolve().parents[3] / "assets" / "lesson-content"
    lesson_directory = tmp_path / "lessons"
    shutil.copytree(source_directory, lesson_directory)
    app = create_app(
        Settings(mode="fake", lesson_directory=str(lesson_directory)),
        renderer=FakeRendererControl(),
    )

    with TestClient(app) as client:
        (lesson_directory / "broken.json").write_text("not JSON", encoding="utf-8")
        deadline = time.monotonic() + 3
        health = client.get("/health").json()
        while health["lesson_catalog_status"] != "reload_error" and time.monotonic() < deadline:
            time.sleep(0.1)
            health = client.get("/health").json()

    assert health["lesson_catalog_status"] == "reload_error"
    assert health["lesson_count"] == 4


def test_unknown_lesson_scene_template_stops_host_startup(tmp_path: Path) -> None:
    source = (
        Path(__file__).resolve().parents[3] / "assets" / "lesson-content" / "cafe-ordering.json"
    )
    lesson = json.loads(source.read_text(encoding="utf-8"))
    lesson["scene_template_id"] = "library"
    (tmp_path / "invalid-scene.json").write_text(
        json.dumps(lesson),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="scene_template_id is not allow-listed"):
        create_app(Settings(mode="fake", lesson_directory=str(tmp_path)))


def test_release_pairing_and_control_authentication(tmp_path) -> None:
    credential_file = tmp_path / "gateway.json"
    authority = PairingAuthority(credential_file)
    code, _ = authority.create_pairing_code()
    device_id = str(uuid4())
    app = create_app(
        Settings(gateway_credentials_file=str(credential_file)),
        renderer=FakeRendererControl(),
    )

    with TestClient(app) as client:
        pairing = client.post(
            "/v1/pairing",
            json=envelope(
                "pairing.request",
                {
                    "code": code,
                    "device_id": device_id,
                    "device_name": "Test phone",
                },
            ),
        )
        assert pairing.status_code == 200
        credential = pairing.json()["payload"]["credential"]

        with client.websocket_connect("/v1/control") as socket:
            socket.send_json(
                envelope(
                    "auth.request",
                    {"device_id": device_id, "credential": credential},
                )
            )
            assert socket.receive_json()["message_type"] == "auth.ok"
            socket.send_json(
                envelope(
                    "session.start",
                    {
                        "client_id": str(uuid4()),
                        "scenario_id": "cafe-ordering",
                        "english_locale": "en-GB",
                        "spaced_review_enabled": False,
                    },
                )
            )
            assert socket.receive_json()["message_type"] == "session.state"


def test_release_control_rejects_missing_device_authentication(tmp_path) -> None:
    app = create_app(
        Settings(gateway_credentials_file=str(tmp_path / "gateway.json")),
        renderer=FakeRendererControl(),
    )
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("session.start", {}))
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()


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


def test_selected_scenario_is_reported_in_teacher_progress() -> None:
    renderer = FakeRendererControl()
    app = create_app(Settings(), renderer=renderer)
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(
            envelope(
                "session.start",
                {
                    "client_id": str(uuid4()),
                    "scenario_id": "supermarket-shopping",
                    "english_locale": "en-US",
                    "spaced_review_enabled": True,
                },
            )
        )
        assert socket.receive_json()["payload"]["state"] == "ready"
        turn = socket.receive_json()

    progress = turn["payload"]["lesson_progress"]
    assert progress["scenario_id"] == "supermarket-shopping"
    assert progress["exercise_number"] == 1
    assert progress["difficulty"] == "intermediate"
    assert turn["payload"]["locale"] == "en-US"
    assert "milk" in turn["payload"]["text"].lower()
    assert renderer.commands[0].scene is not None
    assert renderer.commands[0].scene.environment_id == "supermarket"
    assert {item.asset_id for item in renderer.commands[0].scene.objects} == {
        "market-basket",
        "market-crate",
        "market-shelf",
    }
    assert renderer.commands[1].avatar_animation is not None
    assert renderer.commands[1].avatar_animation.speech_energy


def test_completed_lesson_ends_after_final_teacher_playback() -> None:
    app = create_app(
        Settings(),
        renderer=FakeRendererControl(),
        lesson=CompletingLessonService(),
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
        assert socket.receive_json()["message_type"] == "learner.transcript"
        final_turn = socket.receive_json()
        assert final_turn["payload"]["lesson_progress"]["status"] == "completed"

        socket.send_json(
            envelope(
                "teacher.playback_completed",
                {
                    "session_id": session_id,
                    "turn_id": final_turn["payload"]["turn_id"],
                },
            )
        )
        assert socket.receive_json()["payload"]["state"] == "ending"
        ended = socket.receive_json()

    assert ended["message_type"] == "session.ended"
    assert ended["payload"]["reason"] == "completed"
    assert app.state.session_registry.active_count == 0


def test_selected_word_replay_preserves_awaiting_learner_state() -> None:
    lesson = PronunciationLessonService()
    app = create_app(Settings(), renderer=FakeRendererControl(), lesson=lesson)
    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("session.start", {"client_id": str(uuid4())}))
        assert socket.receive_json()["payload"]["state"] == "ready"
        turn = socket.receive_json()
        session_id = turn["payload"]["session_id"]
        turn_id = turn["payload"]["turn_id"]
        assert turn["payload"]["pronunciations"][0]["ipa"] == "ˈwɛlkəm"

        socket.send_json(
            envelope(
                "teacher.playback_completed",
                {"session_id": session_id, "turn_id": turn_id},
            )
        )
        assert socket.receive_json()["payload"]["state"] == "awaiting_learner"
        socket.send_json(
            envelope(
                "teacher.word_replay_requested",
                {
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "word_index": 0,
                    "playback_rate": 0.75,
                },
            )
        )
        replay = socket.receive_json()

    assert replay["message_type"] == "teacher.word_audio"
    assert replay["payload"]["word"] == "Welcome"
    assert replay["payload"]["sample_rate_hz"] == 16_000
    assert lesson.replays == [("Welcome", "en-GB", 0.75)]


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


def test_invalid_cloud_credential_is_recoverable_and_does_not_crash() -> None:
    cloud_speech = OpenAiCompatibleSpeechProvider(
        "https://provider.example/v1",
        "test-tts",
        "test-voice",
        "missing-target",
        InMemoryCredentialStore(),
        CloudAccessPolicy(offline_only=False),
    )
    lesson = FakeLessonService()
    lesson.speech = cloud_speech  # type: ignore[assignment]
    app = create_app(Settings(), renderer=FakeRendererControl(), lesson=lesson)

    with TestClient(app).websocket_connect("/v1/control") as socket:
        socket.send_json(envelope("session.start", {"client_id": str(uuid4())}))
        assert socket.receive_json()["payload"]["state"] == "ready"
        assert socket.receive_json()["payload"]["state"] == "recoverable_error"
        failure = socket.receive_json()

    assert failure["message_type"] == "error"
    assert failure["payload"]["code"] == "provider_failed"
    assert app.state.session_registry.active_count == 0


def test_no_speech_emits_repeat_turn_without_an_invented_transcript() -> None:
    app = create_app(
        Settings(),
        renderer=FakeRendererControl(),
        lesson=NoSpeechLessonService(),
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
        next_message = socket.receive_json()

    assert next_message["message_type"] == "teacher.turn"
    assert next_message["payload"]["text"] == "Please try again."


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
        renderer_socket.send_json(
            envelope(
                "renderer.teacher_profile_selected",
                {"profile_id": "daniel"},
            )
        )
        assert client.get("/health").json()["teacher_profile"] == "daniel"

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
