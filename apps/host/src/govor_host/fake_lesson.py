"""Deterministic fake lesson providers used only by Milestone 2 development and tests.

The fakes exercise production-shaped provider boundaries without credentials or models. They
never inspect, retain, or log microphone content. The short tones are transport/playback fixtures,
not synthetic speech and must never be presented as a production TTS result.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from dataclasses import dataclass

from govor_contracts import ProviderCapabilities


@dataclass(frozen=True, slots=True)
class AudioReference:
    """Ephemeral reference to an utterance carried by the active WebRTC session."""

    duration_us: int


@dataclass(frozen=True, slots=True)
class FakeTranscript:
    text: str
    locale: str
    provider_id: str = "fake-scripted-stt"


@dataclass(frozen=True, slots=True)
class FakeDialogueReply:
    text: str
    locale: str
    provider_id: str = "fake-scripted-dialogue"


@dataclass(frozen=True, slots=True)
class FakeTeacherTurn:
    text: str
    locale: str
    audio_wav: bytes
    duration_us: int
    provider_id: str = "fake-scripted-speech"


@dataclass(frozen=True, slots=True)
class FakeLessonResult:
    transcript: FakeTranscript
    turn: FakeTeacherTurn


class FakeSpeechRecognizer:
    capabilities = ProviderCapabilities(
        provider_id="fake-scripted-stt",
        provider_kind="speech_recognition",
        local=True,
        features=frozenset({"deterministic", "development_only"}),
    )

    async def transcribe(self, audio: AudioReference) -> FakeTranscript:
        if not 1 <= audio.duration_us <= 30_000_000:
            raise ValueError("utterance duration is outside the accepted range")
        return FakeTranscript(text="I would like coffee, please.", locale="en-GB")


class FakeDialogueProvider:
    capabilities = ProviderCapabilities(
        provider_id="fake-scripted-dialogue",
        provider_kind="dialogue",
        local=True,
        features=frozenset({"deterministic", "development_only"}),
    )

    async def reply(self, transcript: FakeTranscript) -> FakeDialogueReply:
        if not transcript.text:
            raise ValueError("transcript must not be empty")
        return FakeDialogueReply(
            text="Thank you. Would you like coffee or tea?",
            locale="en-GB",
        )


class FakeSpeechProvider:
    capabilities = ProviderCapabilities(
        provider_id="fake-scripted-speech",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset({"deterministic", "development_only", "wav"}),
    )

    async def synthesize(
        self,
        reply: FakeDialogueReply,
        *,
        frequency_hz: float,
    ) -> FakeTeacherTurn:
        audio, duration_us = _tone_wav(frequency_hz=frequency_hz)
        return FakeTeacherTurn(
            text=reply.text,
            locale=reply.locale,
            audio_wav=audio,
            duration_us=duration_us,
        )


class FakeLessonService:
    """Production-shaped deterministic pipeline composed from unmistakable fakes."""

    def __init__(
        self,
        recognizer: FakeSpeechRecognizer | None = None,
        dialogue: FakeDialogueProvider | None = None,
        speech: FakeSpeechProvider | None = None,
    ) -> None:
        self.recognizer = recognizer or FakeSpeechRecognizer()
        self.dialogue = dialogue or FakeDialogueProvider()
        self.speech = speech or FakeSpeechProvider()

    @property
    def capabilities(self) -> tuple[ProviderCapabilities, ...]:
        return (
            self.recognizer.capabilities,
            self.dialogue.capabilities,
            self.speech.capabilities,
        )

    async def initial_turn(self) -> FakeTeacherTurn:
        return await self.speech.synthesize(
            FakeDialogueReply(
                text="Welcome. What would you like to order?",
                locale="en-GB",
            ),
            frequency_hz=440.0,
        )

    async def respond(self, audio: AudioReference) -> FakeLessonResult:
        transcript = await self.recognizer.transcribe(audio)
        reply = await self.dialogue.reply(transcript)
        turn = await self.speech.synthesize(reply, frequency_hz=554.37)
        return FakeLessonResult(transcript=transcript, turn=turn)


def _tone_wav(*, frequency_hz: float, duration_seconds: float = 0.15) -> tuple[bytes, int]:
    sample_rate = 16_000
    frame_count = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        for index in range(frame_count):
            fade = min(1.0, index / 160, (frame_count - index) / 160)
            sample = int(5_000 * fade * math.sin(2 * math.pi * frequency_hz * index / sample_rate))
            output.writeframesraw(struct.pack("<h", sample))
    return buffer.getvalue(), frame_count * 1_000_000 // sample_rate
