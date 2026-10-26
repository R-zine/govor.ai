from __future__ import annotations

import io
import json
import logging
import wave
from uuid import uuid4

import httpx
import pytest
from govor_domain import CAFE_LESSON, DetectedLanguage, LearnerIntent
from govor_provider_interfaces import (
    DialogueRequest,
    ProviderAuthenticationError,
    ProviderMalformedOutput,
    ProviderUnavailable,
    Transcript,
    UtteranceAudio,
)
from govor_provider_router import (
    CloudAccessPolicy,
    InMemoryCredentialStore,
    OpenAiCompatibleDialogueProvider,
    OpenAiCompatibleSpeechProvider,
    OpenAiCompatibleSpeechRecognizer,
)


def request() -> DialogueRequest:
    return DialogueRequest(
        transcript=Transcript(
            text="Coffee, please.",
            locale="en-GB",
            language=DetectedLanguage.ENGLISH,
            provider_id="fixture",
        ),
        lesson=CAFE_LESSON,
        history=(),
        intent_hint=LearnerIntent.ENGLISH_ANSWER,
    )


def wav_bytes() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\0\0" * 1_600)
    return output.getvalue()


def credentials() -> InMemoryCredentialStore:
    return InMemoryCredentialStore({"test-provider": "SUPER-SECRET-KEY"})


@pytest.mark.asyncio
async def test_dialogue_uses_compatible_schema_and_safe_authorization() -> None:
    seen: dict[str, object] = {}

    def handler(http_request: httpx.Request) -> httpx.Response:
        seen["authorization"] = http_request.headers["authorization"]
        seen["body"] = json.loads(http_request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "intent": "english_answer",
                                    "reply_text": "Would you like anything else?",
                                    "reply_locale": "en-GB",
                                    "advance_exercise": True,
                                }
                            )
                        }
                    }
                ]
            },
        )

    provider = OpenAiCompatibleDialogueProvider(
        "https://provider.example/v1",
        "test-model",
        "test-provider",
        credentials(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(handler),
    )

    result = await provider.generate(request())

    assert result.advance_exercise
    assert seen["authorization"] == "Bearer SUPER-SECRET-KEY"
    body = seen["body"]
    assert isinstance(body, dict)
    assert body["response_format"]["type"] == "json_schema"


@pytest.mark.asyncio
async def test_offline_gate_prevents_network_and_credential_access() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200)

    provider = OpenAiCompatibleDialogueProvider(
        "https://provider.example/v1",
        "test-model",
        "missing-target",
        InMemoryCredentialStore(),
        CloudAccessPolicy(offline_only=True),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderUnavailable, match="offline-only"):
        await provider.generate(request())
    assert not called


@pytest.mark.asyncio
async def test_missing_and_rejected_credentials_are_typed_and_not_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    missing = OpenAiCompatibleDialogueProvider(
        "https://provider.example/v1",
        "test-model",
        "missing-target",
        InMemoryCredentialStore(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(lambda _: httpx.Response(200)),
    )
    with pytest.raises(ProviderAuthenticationError, match="not configured"):
        await missing.generate(request())

    rejected = OpenAiCompatibleDialogueProvider(
        "https://provider.example/v1",
        "test-model",
        "test-provider",
        credentials(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(lambda _: httpx.Response(401, text="PRIVATE-BODY")),
    )
    with pytest.raises(ProviderAuthenticationError, match="rejected"):
        await rejected.generate(request())

    assert "SUPER-SECRET-KEY" not in caplog.text
    assert "PRIVATE-BODY" not in caplog.text
    assert "Coffee, please" not in caplog.text


@pytest.mark.asyncio
async def test_cloud_response_is_bounded_while_streaming() -> None:
    provider = OpenAiCompatibleDialogueProvider(
        "https://provider.example/v1",
        "test-model",
        "test-provider",
        credentials(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 65_537)),
    )

    with pytest.raises(ProviderMalformedOutput, match="byte limit"):
        await provider.generate(request())


@pytest.mark.asyncio
async def test_recognition_upload_is_ephemeral_and_returns_bounded_text() -> None:
    def handler(http_request: httpx.Request) -> httpx.Response:
        assert b'filename="utterance.wav"' in http_request.content
        assert b"RIFF" in http_request.content
        return httpx.Response(200, json={"text": "Coffee, please."})

    provider = OpenAiCompatibleSpeechRecognizer(
        "https://provider.example/v1",
        "test-stt",
        "test-provider",
        credentials(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(handler),
    )
    result = await provider.transcribe(
        UtteranceAudio(uuid4(), duration_us=100_000, wav_bytes=wav_bytes())
    )

    assert result.text == "Coffee, please."
    assert result.language is DetectedLanguage.ENGLISH
    assert not provider.capabilities.local


@pytest.mark.asyncio
async def test_speech_returns_actual_wav_with_null_timing() -> None:
    audio = wav_bytes()
    provider = OpenAiCompatibleSpeechProvider(
        "https://provider.example/v1",
        "test-tts",
        "test-voice",
        "test-provider",
        credentials(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=audio)),
    )

    turn = await provider.synthesize("Hello.", "en-GB")

    assert turn.audio_wav == audio
    assert turn.duration_us == 100_000
    assert turn.word_alignment is None
    assert turn.phoneme_alignment is None


@pytest.mark.asyncio
async def test_speech_uses_current_teacher_profile_voice() -> None:
    seen_voices: list[str] = []
    selected_voice = "female-presentation"

    def handler(http_request: httpx.Request) -> httpx.Response:
        body = json.loads(http_request.content)
        seen_voices.append(body["voice"])
        return httpx.Response(200, content=wav_bytes())

    provider = OpenAiCompatibleSpeechProvider(
        "https://provider.example/v1",
        "test-tts",
        "default-presentation",
        "test-provider",
        credentials(),
        CloudAccessPolicy(offline_only=False),
        transport=httpx.MockTransport(handler),
        voice_provider=lambda: selected_voice,
    )

    await provider.synthesize("Hello.", "en-GB")
    selected_voice = "male-presentation"
    await provider.synthesize("Hello again.", "en-GB")

    assert seen_voices == ["female-presentation", "male-presentation"]
