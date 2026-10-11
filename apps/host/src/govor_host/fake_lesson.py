"""Deterministic fake lesson providers used only by development and tests.

The fakes exercise production-shaped provider boundaries without credentials or models. They
never inspect, retain, or log microphone content. The short tones are transport/playback fixtures,
not synthetic speech and must never be presented as a production TTS result.
"""

from __future__ import annotations

import io
import math
import struct
import wave

from govor_contracts import ProviderCapabilities
from govor_domain import DetectedLanguage
from govor_provider_interfaces import LessonResult, TeacherTurn, Transcript, UtteranceAudio


class FakeSpeechRecognizer:
    capabilities = ProviderCapabilities(
        provider_id="fake-scripted-stt",
        provider_kind="speech_recognition",
        local=True,
        features=frozenset({"deterministic", "development_only"}),
    )

    async def transcribe(self, audio: UtteranceAudio) -> Transcript:
        if not 1 <= audio.duration_us <= 30_000_000:
            raise ValueError("utterance duration is outside the accepted range")
        return Transcript(
            text="I would like coffee, please.",
            locale="en-GB",
            language=DetectedLanguage.ENGLISH,
            provider_id="fake-scripted-stt",
        )


class FakeDialogueProvider:
    capabilities = ProviderCapabilities(
        provider_id="fake-scripted-dialogue",
        provider_kind="dialogue",
        local=True,
        features=frozenset({"deterministic", "development_only"}),
    )

    async def reply(self, transcript: Transcript) -> tuple[str, str]:
        if not transcript.text:
            raise ValueError("transcript must not be empty")
        return "Thank you. Would you like coffee or tea?", "en-GB"


class FakeSpeechProvider:
    capabilities = ProviderCapabilities(
        provider_id="fake-scripted-speech",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset({"deterministic", "development_only", "wav"}),
    )

    async def synthesize(
        self,
        text: str,
        locale: str,
        *,
        frequency_hz: float,
    ) -> TeacherTurn:
        audio, duration_us = _tone_wav(frequency_hz=frequency_hz)
        return TeacherTurn(
            text=text,
            locale=locale,
            audio_wav=audio,
            duration_us=duration_us,
            provider_id="fake-scripted-speech",
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

    async def initial_turn(self) -> TeacherTurn:
        return await self.speech.synthesize(
            "Welcome. What would you like to order?",
            "en-GB",
            frequency_hz=440.0,
        )

    async def respond(self, audio: UtteranceAudio) -> LessonResult:
        transcript = await self.recognizer.transcribe(audio)
        text, locale = await self.dialogue.reply(transcript)
        turn = await self.speech.synthesize(text, locale, frequency_hz=554.37)
        return LessonResult(transcript=transcript, turn=turn)


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
