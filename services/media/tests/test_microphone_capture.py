from __future__ import annotations

import io
import wave
from uuid import uuid4

import numpy as np
import pytest

pytest.importorskip("av")

from av import AudioFrame
from fastapi.testclient import TestClient
from govor_media.app import create_media_app
from govor_media.microphone_capture import CaptureConflict, CaptureEmpty, MicrophoneCapture

TOKEN = "test-only-pairing-token-32-characters"  # noqa: S105


def audio_frame() -> AudioFrame:
    frame = AudioFrame(format="s16", layout="mono", samples=320)
    frame.sample_rate = 16_000
    samples = (np.sin(np.arange(320) * 0.1) * 4_000).astype("<i2")
    frame.planes[0].update(samples.tobytes())
    return frame


def audio_frame_48khz() -> AudioFrame:
    frame = AudioFrame(format="s16", layout="mono", samples=960)
    frame.sample_rate = 48_000
    samples = (np.sin(np.arange(960) * 0.1) * 4_000).astype("<i2")
    frame.planes[0].update(samples.tobytes())
    return frame


def test_capture_emits_bounded_mono_16khz_wav_and_forgets_pcm() -> None:
    capture = MicrophoneCapture()
    utterance_id = uuid4()
    capture.begin(utterance_id)
    capture.append(audio_frame())

    output = capture.finish(utterance_id)

    with wave.open(io.BytesIO(output), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16_000
        assert wav.getnframes() == 320
    assert capture.active_utterance_id is None


def test_capture_rejects_mismatched_or_empty_utterance() -> None:
    capture = MicrophoneCapture()
    utterance_id = uuid4()
    capture.begin(utterance_id)
    with pytest.raises(CaptureConflict):
        capture.finish(uuid4())
    with pytest.raises(CaptureEmpty):
        capture.finish(utterance_id)


def test_capture_flushes_resampler_delay_for_48khz_webrtc_audio() -> None:
    capture = MicrophoneCapture()
    utterance_id = uuid4()
    capture.begin(utterance_id)
    capture.append(audio_frame_48khz())

    output = capture.finish(utterance_id)

    with wave.open(io.BytesIO(output), "rb") as wav:
        assert wav.getframerate() == 16_000
        assert wav.getnframes() == 320


def test_capture_http_handoff_is_loopback_only_and_no_store() -> None:
    app = create_media_app(pairing_token=TOKEN)
    utterance_id = uuid4()
    with TestClient(app, client=("127.0.0.1", 50_000)) as client:
        start = client.post(
            "/v1/internal/microphone/start",
            json={"utterance_id": str(utterance_id)},
        )
        app.state.microphone_capture.append(audio_frame())
        finish = client.post(
            "/v1/internal/microphone/finish",
            json={"utterance_id": str(utterance_id)},
        )

    assert start.status_code == 204
    assert finish.status_code == 200
    assert finish.headers["cache-control"] == "no-store"
    assert finish.content.startswith(b"RIFF")


def test_capture_http_handoff_rejects_non_loopback_client() -> None:
    app = create_media_app(pairing_token=TOKEN)
    with TestClient(app, client=("192.0.2.10", 50_000)) as client:
        response = client.post(
            "/v1/internal/microphone/start",
            json={"utterance_id": str(uuid4())},
        )

    assert response.status_code == 403
