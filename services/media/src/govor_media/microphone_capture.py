"""Bounded in-memory capture of an active WebRTC microphone utterance."""

from __future__ import annotations

import io
import wave
from uuid import UUID

from av import AudioFrame
from av.audio.resampler import AudioResampler


class CaptureConflict(ValueError):
    pass


class CaptureEmpty(ValueError):
    pass


class MicrophoneCapture:
    sample_rate_hz = 16_000
    max_pcm_bytes = sample_rate_hz * 2 * 30

    def __init__(self) -> None:
        self._utterance_id: UUID | None = None
        self._pcm = bytearray()
        self._overflowed = False
        self._resampler: AudioResampler | None = None

    @property
    def active_utterance_id(self) -> UUID | None:
        return self._utterance_id

    def begin(self, utterance_id: UUID) -> None:
        if self._utterance_id is not None and self._utterance_id != utterance_id:
            raise CaptureConflict("another microphone capture is active")
        self._utterance_id = utterance_id
        self._pcm.clear()
        self._overflowed = False
        self._resampler = AudioResampler(format="s16", layout="mono", rate=self.sample_rate_hz)

    def append(self, frame: AudioFrame) -> None:
        if self._utterance_id is None or self._resampler is None:
            return
        for converted in self._resampler.resample(frame):
            self._append_converted(converted)
            if self._overflowed:
                return

    def finish(self, utterance_id: UUID) -> bytes:
        if self._utterance_id != utterance_id:
            raise CaptureConflict("utterance does not match the active microphone capture")
        try:
            if self._resampler is not None:
                for converted in self._resampler.resample(None):
                    self._append_converted(converted)
            if self._overflowed:
                raise CaptureConflict("microphone capture exceeded the 30 second bound")
            if not self._pcm:
                raise CaptureEmpty("microphone capture contains no audio frames")
            output = io.BytesIO()
            with wave.open(output, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate_hz)
                wav.writeframes(self._pcm)
            return output.getvalue()
        finally:
            self.cancel(utterance_id)

    def cancel(self, utterance_id: UUID | None = None) -> None:
        if utterance_id is not None and self._utterance_id not in {None, utterance_id}:
            raise CaptureConflict("utterance does not match the active microphone capture")
        self._utterance_id = None
        self._pcm.clear()
        self._overflowed = False
        self._resampler = None

    def _append_converted(self, frame: AudioFrame) -> None:
        samples = frame.to_ndarray().astype("<i2", copy=False).tobytes()
        remaining = self.max_pcm_bytes - len(self._pcm)
        if len(samples) > remaining:
            self._pcm.extend(samples[:remaining])
            self._overflowed = True
            return
        self._pcm.extend(samples)
