"""Explicitly opt-in OpenAI-compatible cloud provider adapters."""

from __future__ import annotations

import io
import wave
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from govor_contracts import ProviderCapabilities
from govor_domain import DialogueDraft, detect_language
from govor_provider_interfaces import (
    DIALOGUE_JSON_SCHEMA,
    DialogueRequest,
    ProviderAuthenticationError,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
    TeacherTurn,
    Transcript,
    UtteranceAudio,
    dialogue_messages,
    parse_dialogue_content,
)

from .secrets import CredentialStore, validate_credential_target


@dataclass(slots=True)
class CloudAccessPolicy:
    offline_only: bool = True

    def require_enabled(self) -> None:
        if self.offline_only:
            raise ProviderUnavailable("cloud access is disabled by offline-only mode")


class _CloudAdapter:
    def __init__(
        self,
        base_url: str,
        credential_target: str,
        credentials: CredentialStore,
        policy: CloudAccessPolicy,
        *,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("cloud provider URL must use HTTPS")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("cloud provider URL must not contain credentials or parameters")
        self._base_url = base_url.rstrip("/")
        self._credential_target = validate_credential_target(credential_target)
        self._credentials = credentials
        self._policy = policy
        self._timeout = timeout_seconds
        self._transport = transport

    async def _post(
        self,
        path: str,
        *,
        json_body: Any | None = None,
        data: Mapping[str, str] | None = None,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
        max_response_bytes: int = 65_536,
    ) -> httpx.Response:
        self._policy.require_enabled()
        secret = self._credentials.get_secret(self._credential_target)
        try:
            async with (
                httpx.AsyncClient(
                    timeout=self._timeout,
                    transport=self._transport,
                ) as client,
                client.stream(
                    "POST",
                    f"{self._base_url}{path}",
                    headers={"Authorization": f"Bearer {secret}"},
                    json=json_body,
                    data=data,
                    files=files,
                ) as streamed,
            ):
                if streamed.status_code in {401, 403}:
                    raise ProviderAuthenticationError("cloud provider rejected the credential")
                if streamed.status_code == 429:
                    raise ProviderResourceExhausted("cloud provider rate limit was reached")
                if streamed.status_code >= 400:
                    raise ProviderUnavailable("cloud provider request failed")
                content = bytearray()
                async for chunk in streamed.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_response_bytes:
                        raise ProviderMalformedOutput(
                            "cloud provider response exceeded the byte limit"
                        )
                response = httpx.Response(
                    streamed.status_code,
                    headers=streamed.headers,
                    content=bytes(content),
                    request=streamed.request,
                )
        except httpx.TimeoutException as error:
            raise TimeoutError("cloud provider request timed out") from error
        except httpx.HTTPError as error:
            raise ProviderUnavailable("cloud provider is unavailable") from error
        return response


class OpenAiCompatibleDialogueProvider(_CloudAdapter):
    def __init__(
        self,
        base_url: str,
        model: str,
        credential_target: str,
        credentials: CredentialStore,
        policy: CloudAccessPolicy,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            base_url,
            credential_target,
            credentials,
            policy,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        self._model = _bounded_name(model, "dialogue model")
        self.capabilities = ProviderCapabilities(
            provider_id="cloud-openai-compatible-dialogue",
            provider_kind="dialogue",
            local=False,
            features=frozenset({"structured_json", "sends_transcript", "opt_in_cloud"}),
        )

    async def generate(self, request: DialogueRequest) -> DialogueDraft:
        response = await self._post(
            "/chat/completions",
            json_body={
                "model": self._model,
                "messages": dialogue_messages(request),
                "temperature": 0.2,
                "max_tokens": 240,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "govor_dialogue_decision",
                        "strict": True,
                        "schema": DIALOGUE_JSON_SCHEMA,
                    },
                },
            },
        )
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ProviderMalformedOutput("cloud dialogue response was malformed") from error
        return parse_dialogue_content(content, request)


class OpenAiCompatibleSpeechRecognizer(_CloudAdapter):
    def __init__(
        self,
        base_url: str,
        model: str,
        credential_target: str,
        credentials: CredentialStore,
        policy: CloudAccessPolicy,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            base_url,
            credential_target,
            credentials,
            policy,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        self._model = _bounded_name(model, "recognition model")
        self.capabilities = ProviderCapabilities(
            provider_id="cloud-openai-compatible-stt",
            provider_kind="speech_recognition",
            local=False,
            features=frozenset(
                {"uploads_microphone_audio", "opt_in_cloud", "no_recording_requested"}
            ),
        )

    async def transcribe(self, audio: UtteranceAudio) -> Transcript:
        if audio.wav_bytes is None:
            raise ProviderUnavailable("cloud recognition requires captured WAV audio")
        response = await self._post(
            "/audio/transcriptions",
            data={"model": self._model, "response_format": "json"},
            files={"file": ("utterance.wav", audio.wav_bytes, "audio/wav")},
        )
        try:
            body = response.json()
            text = body["text"]
            if not isinstance(text, str) or not text.strip() or len(text) > 8_192:
                raise ValueError("text is empty or unbounded")
        except (ValueError, KeyError, TypeError) as error:
            raise ProviderMalformedOutput("cloud recognition response was malformed") from error
        language = detect_language(text)
        return Transcript(
            text=text.strip(),
            locale="bg-BG" if language.value == "bg" else "en-GB",
            language=language,
            provider_id=self.capabilities.provider_id,
        )


class OpenAiCompatibleSpeechProvider(_CloudAdapter):
    def __init__(
        self,
        base_url: str,
        model: str,
        voice: str,
        credential_target: str,
        credentials: CredentialStore,
        policy: CloudAccessPolicy,
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        voice_provider: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(
            base_url,
            credential_target,
            credentials,
            policy,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
        self._model = _bounded_name(model, "speech model")
        self._voice = _bounded_name(voice, "speech voice")
        self._voice_provider = voice_provider
        self.capabilities = ProviderCapabilities(
            provider_id="cloud-openai-compatible-tts",
            provider_kind="speech_synthesis",
            local=False,
            features=frozenset({"sends_teacher_text", "opt_in_cloud", "wav", "timing_unavailable"}),
        )

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        response = await self._post(
            "/audio/speech",
            json_body={
                "model": self._model,
                "voice": _bounded_name(
                    self._voice_provider() if self._voice_provider is not None else self._voice,
                    "speech voice",
                ),
                "input": text,
                "response_format": "wav",
                "speed": speed,
            },
            max_response_bytes=1_500_044,
        )
        audio = response.content
        try:
            with wave.open(io.BytesIO(audio), "rb") as wav:
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                width = wav.getsampwidth()
                frames = wav.getnframes()
        except (EOFError, wave.Error) as error:
            raise ProviderMalformedOutput("cloud speech response was not valid WAV") from error
        if (
            channels != 1
            or width != 2
            or frames <= 0
            or sample_rate not in {16_000, 22_050, 24_000, 48_000}
        ):
            raise ProviderMalformedOutput("cloud speech WAV format was unsupported")
        duration_us = frames * 1_000_000 // sample_rate
        try:
            return TeacherTurn(
                text=text,
                locale=locale,
                audio_wav=audio,
                sample_rate_hz=sample_rate,
                duration_us=duration_us,
                provider_id=self.capabilities.provider_id,
                word_alignment=None,
                phoneme_alignment=None,
            )
        except ValueError as error:
            raise ProviderMalformedOutput("cloud speech WAV was outside accepted bounds") from error


def _bounded_name(value: str, label: str) -> str:
    if not value or len(value) > 128 or any(character.isspace() for character in value):
        raise ValueError(f"{label} must be a non-empty bounded identifier")
    return value
