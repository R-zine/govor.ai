"""Small PCM/WAV helpers shared by local speech adapters."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from typing import Any


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


def pitch_shift_pcm16_wav(value: bytes, semitones: float) -> bytes:
    """Shift pitch while preserving frame count, using an in-process phase vocoder."""

    if not 0.5 <= semitones <= 6.0:
        raise ValueError("speech pitch shift is outside the accepted range")
    info = inspect_wav(value)
    try:
        with wave.open(io.BytesIO(value), "rb") as wav:
            pcm = wav.readframes(info.frame_count)
        import numpy as np

        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32768.0
        rate = 2.0 ** (-semitones / 12.0)
        stretched = _time_stretch(samples, rate)
        positions = np.linspace(0.0, float(len(stretched) - 1), info.frame_count)
        shifted = np.interp(positions, np.arange(len(stretched)), stretched)
        peak = float(np.max(np.abs(shifted)))
        if peak > 0.98:
            shifted *= 0.98 / peak
        shifted_pcm = np.rint(np.clip(shifted, -1.0, 1.0) * 32767.0).astype("<i2")
    except Exception as error:
        raise ValueError("speech pitch shift failed") from error
    return pcm16_wav(shifted_pcm.tobytes(), info.sample_rate_hz)


def _time_stretch(samples: Any, rate: float) -> Any:
    """Small NumPy phase vocoder used only for the bounded Bulgarian presentation shift."""

    import numpy as np

    values = np.asarray(samples, dtype=np.float64)
    if values.size < 32:
        raise ValueError("speech sample is too short to shift")
    n_fft = 1024 if values.size >= 1024 else 2 ** int(np.floor(np.log2(values.size)))
    n_fft = max(32, n_fft)
    hop = n_fft // 4
    window = np.hanning(n_fft)
    padding = n_fft // 2
    padded = np.pad(values, (padding, padding), mode="reflect")
    frame_count = 1 + max(0, (len(padded) - n_fft) // hop)
    frames = np.stack(
        [padded[index * hop : index * hop + n_fft] * window for index in range(frame_count)]
    )
    spectrum = np.fft.rfft(frames, axis=1).T
    time_steps = np.arange(0.0, spectrum.shape[1] - 1, rate)
    output_spectrum = np.empty((spectrum.shape[0], len(time_steps)), dtype=np.complex128)
    phase = np.angle(spectrum[:, 0])
    phase_advance = 2.0 * np.pi * hop * np.arange(spectrum.shape[0]) / n_fft
    for output_index, step in enumerate(time_steps):
        source_index = int(step)
        fraction = step - source_index
        left = spectrum[:, source_index]
        right = spectrum[:, source_index + 1]
        magnitude = (1.0 - fraction) * np.abs(left) + fraction * np.abs(right)
        output_spectrum[:, output_index] = magnitude * np.exp(1j * phase)
        delta = np.angle(right) - np.angle(left) - phase_advance
        delta -= 2.0 * np.pi * np.round(delta / (2.0 * np.pi))
        phase += phase_advance + delta

    output_length = max(n_fft, (output_spectrum.shape[1] - 1) * hop + n_fft)
    output = np.zeros(output_length, dtype=np.float64)
    window_sum = np.zeros(output_length, dtype=np.float64)
    reconstructed = np.fft.irfft(output_spectrum.T, n=n_fft, axis=1)
    for index, frame in enumerate(reconstructed):
        start = index * hop
        output[start : start + n_fft] += frame * window
        window_sum[start : start + n_fft] += window * window
    nonzero = window_sum > 1e-10
    output[nonzero] /= window_sum[nonzero]
    target_length = max(1, round(values.size / rate))
    trimmed = output[padding : padding + target_length]
    if len(trimmed) < target_length:
        trimmed = np.pad(trimmed, (0, target_length - len(trimmed)))
    return trimmed
