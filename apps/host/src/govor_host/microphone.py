"""Ephemeral handoff from the WebRTC media peer to host recognition."""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urlparse
from uuid import UUID

import httpx
from govor_provider_interfaces import ProviderUnavailable, UtteranceAudio


class MicrophoneAudioSource(Protocol):
    async def begin(self, utterance_id: UUID) -> None: ...

    async def finish(self, utterance_id: UUID, duration_us: int) -> UtteranceAudio: ...

    async def cancel(self, utterance_id: UUID | None = None) -> None: ...


class ReferenceOnlyMicrophoneSource:
    """Fake-mode source that intentionally never claims to contain microphone samples."""

    async def begin(self, utterance_id: UUID) -> None:
        _ = utterance_id

    async def finish(self, utterance_id: UUID, duration_us: int) -> UtteranceAudio:
        return UtteranceAudio(
            utterance_id=utterance_id,
            duration_us=duration_us,
            wav_bytes=None,
        )

    async def cancel(self, utterance_id: UUID | None = None) -> None:
        _ = utterance_id


class MediaMicrophoneSource:
    """Loopback-only client for the bounded media-service capture buffer."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 2.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("microphone capture service must use loopback HTTP")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("microphone capture URL must not contain credentials or parameters")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def begin(self, utterance_id: UUID) -> None:
        await self._post("start", utterance_id)

    async def finish(self, utterance_id: UUID, duration_us: int) -> UtteranceAudio:
        response = await self._post("finish", utterance_id)
        wav_bytes = response.content
        return UtteranceAudio(
            utterance_id=utterance_id,
            duration_us=duration_us,
            wav_bytes=wav_bytes,
        )

    async def cancel(self, utterance_id: UUID | None = None) -> None:
        payload = {"utterance_id": str(utterance_id)} if utterance_id is not None else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                await client.post(f"{self._base_url}/v1/internal/microphone/cancel", json=payload)
        except httpx.HTTPError:
            return

    async def _post(self, action: str, utterance_id: UUID) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/v1/internal/microphone/{action}",
                    json={"utterance_id": str(utterance_id)},
                )
                response.raise_for_status()
                return response
        except httpx.HTTPError as error:
            raise ProviderUnavailable("microphone capture service is unavailable") from error
