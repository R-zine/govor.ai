from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from govor_host.microphone import MediaMicrophoneSource, ReferenceOnlyMicrophoneSource
from govor_provider_interfaces import ProviderUnavailable


@pytest.mark.asyncio
async def test_reference_source_returns_metadata_without_inventing_audio() -> None:
    source = ReferenceOnlyMicrophoneSource()
    utterance_id = uuid4()

    await source.begin(utterance_id)
    result = await source.finish(utterance_id, 500_000)
    await source.cancel(utterance_id)

    assert result.utterance_id == utterance_id
    assert result.wav_bytes is None


def test_media_source_rejects_non_loopback_and_parameterized_urls() -> None:
    with pytest.raises(ValueError, match="loopback"):
        MediaMicrophoneSource("http://192.168.1.2:8766")
    with pytest.raises(ValueError, match="parameters"):
        MediaMicrophoneSource("http://127.0.0.1:8766?token=secret")


@pytest.mark.asyncio
async def test_media_source_uses_bounded_loopback_capture_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    utterance_id = uuid4()
    wav = b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 32
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        content = wav if request.url.path.endswith("/finish") else b""
        return httpx.Response(200, content=content, request=request)

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "govor_host.microphone.httpx.AsyncClient",
        lambda **kwargs: async_client(transport=transport, **kwargs),
    )
    source = MediaMicrophoneSource("http://127.0.0.1:8766")

    await source.begin(utterance_id)
    result = await source.finish(utterance_id, 500_000)
    await source.cancel(utterance_id)

    assert result.wav_bytes == wav
    assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == [
        "start",
        "finish",
        "cancel",
    ]


@pytest.mark.asyncio
async def test_media_source_redacts_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "govor_host.microphone.httpx.AsyncClient",
        lambda **kwargs: async_client(transport=transport, **kwargs),
    )
    source = MediaMicrophoneSource("http://127.0.0.1:8766")

    with pytest.raises(ProviderUnavailable, match="unavailable"):
        await source.begin(uuid4())
