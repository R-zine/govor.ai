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
from govor_domain import (
    DetectedLanguage,
    LearnerIntent,
    LessonCatalog,
    LessonProgress,
    TeachingEngine,
    load_lesson_catalog,
)
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
        speed: float = 1.0,
        frequency_hz: float = 440.0,
    ) -> TeacherTurn:
        _ = speed
        audio, duration_us = _tone_wav(frequency_hz=frequency_hz)
        return TeacherTurn(
            text=text,
            locale=locale,
            audio_wav=audio,
            sample_rate_hz=16_000,
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
        *,
        catalog: LessonCatalog | None = None,
    ) -> None:
        self.recognizer = recognizer or FakeSpeechRecognizer()
        self.dialogue = dialogue or FakeDialogueProvider()
        self.speech = speech or FakeSpeechProvider()
        self.catalog = catalog or load_lesson_catalog("assets/lesson-content")
        self._engine = TeachingEngine(self.catalog.get(self.catalog.default_scenario_id))

    @property
    def progress(self) -> LessonProgress:
        return self._engine.progress()

    @property
    def capabilities(self) -> tuple[ProviderCapabilities, ...]:
        return (
            self.recognizer.capabilities,
            self.dialogue.capabilities,
            self.speech.capabilities,
        )

    async def initial_turn(
        self,
        scenario_id: str = "cafe-ordering",
        *,
        english_locale: str = "en-GB",
        spaced_review_enabled: bool = False,
    ) -> TeacherTurn:
        _ = spaced_review_enabled
        self._engine = TeachingEngine(
            self.catalog.get(scenario_id),
            english_locale=english_locale,
        )
        return await self.speech.synthesize(
            self._engine.initial_prompt(),
            english_locale,
            frequency_hz=440.0,
        )

    async def replay_word(self, word: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        return await self.speech.synthesize(word, locale, speed=speed)

    async def respond(self, audio: UtteranceAudio) -> LessonResult:
        transcript = await self.recognizer.transcribe(audio)
        self._engine.evaluate(
            transcript.text,
            transcript.language,
            LearnerIntent.ENGLISH_ANSWER,
        )
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
