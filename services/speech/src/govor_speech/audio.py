"""Small PCM/WAV helpers shared by local speech adapters."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WavInfo:
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int

    @property
    def duration_us(self) -> int:
        return self.frame_count * 1_000_000 // self.sample_rate_hz


def pcm16_wav(pcm: bytes, sample_rate_hz: int) -> bytes:
    if sample_rate_hz <= 0 or not pcm or len(pcm) % 2:
        raise ValueError("PCM must contain complete 16-bit mono samples")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate_hz)
        wav.writeframes(pcm)
    return output.getvalue()


def inspect_wav(value: bytes) -> WavInfo:
    try:
        with wave.open(io.BytesIO(value), "rb") as wav:
            info = WavInfo(
                sample_rate_hz=wav.getframerate(),
                channels=wav.getnchannels(),
                sample_width_bytes=wav.getsampwidth(),
                frame_count=wav.getnframes(),
            )
    except (EOFError, wave.Error) as error:
        raise ValueError("speech provider returned an invalid WAV") from error
    if info.channels != 1 or info.sample_width_bytes != 2 or info.frame_count <= 0:
        raise ValueError("speech WAV must be non-empty 16-bit mono PCM")
    return info
