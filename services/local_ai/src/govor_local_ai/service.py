"""Composition of local recognition, structured dialogue, policy, and temporary audio."""

from __future__ import annotations

import io
import math
import struct
import wave
from typing import Protocol

from govor_contracts import ProviderCapabilities
from govor_domain import (
    CAFE_LESSON,
    ConversationMemory,
    ConversationTurn,
    DetectedLanguage,
    DialoguePolicy,
    LearnerIntent,
    Recognition,
    classify_explicit_intent,
)
from govor_provider_interfaces import (
    DialogueProvider,
    DialogueRequest,
    LessonResult,
    NoSpeechRecognized,
    ProviderError,
    SpeechProvider,
    SpeechRecognizer,
    TeacherTurn,
    UtteranceAudio,
)

from .llama_cpp import LlamaCppDialogueProvider
from .whisper_cpp import WhisperCppRecognizer


class LocalAiSettings(Protocol):
    llama_base_url: str
    whisper_executable: str
    whisper_model: str
    provider_timeout_seconds: float
    conversation_memory_turns: int
    dialogue_provider_id: str


class DiagnosticToneSpeechProvider:
    """Temporary audible transport marker; Milestone 4 replaces it with real speech."""

    capabilities = ProviderCapabilities(
        provider_id="milestone3-diagnostic-tone",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset({"development_only", "not_speech", "wav"}),
    )

    async def synthesize(self, text: str, locale: str) -> TeacherTurn:
        audio, duration_us = _tone_wav(440.0 if locale == "en-GB" else 392.0)
        return TeacherTurn(
            text=text,
            locale=locale,
            audio_wav=audio,
            duration_us=duration_us,
            provider_id="milestone3-diagnostic-tone",
        )


class LocalLessonService:
    def __init__(
        self,
        recognizer: SpeechRecognizer,
        dialogue: DialogueProvider,
        speech: SpeechProvider | None = None,
        *,
        memory_turns: int = 8,
    ) -> None:
        self.recognizer = recognizer
        self.dialogue = dialogue
        self.speech = speech or DiagnosticToneSpeechProvider()
        self.memory = ConversationMemory(max_turns=memory_turns)
        self.policy = DialoguePolicy()
        self.lesson = CAFE_LESSON

    @property
    def capabilities(self) -> tuple[ProviderCapabilities, ...]:
        return (
            self.recognizer.capabilities,
            self.dialogue.capabilities,
            self.speech.capabilities,
        )

    async def initial_turn(self) -> TeacherTurn:
        return await self.speech.synthesize(self.lesson.teacher_prompt, "en-GB")

    async def respond(self, audio: UtteranceAudio) -> LessonResult:
        try:
            transcript = await self.recognizer.transcribe(audio)
        except NoSpeechRecognized:
            decision = self.policy.fallback(LearnerIntent.RECOGNITION_ERROR)
            turn = await self.speech.synthesize(decision.reply_text, decision.reply_locale)
            return LessonResult(transcript=None, turn=turn)
        recognition = Recognition(
            text=transcript.text,
            language=transcript.language,
            locale=transcript.locale,
            provider_id=transcript.provider_id,
            confidence=transcript.confidence,
        )
        fallback_intent = _fallback_intent(transcript.text, transcript.language.value)
        intent_hint = classify_explicit_intent(transcript.text, transcript.language)
        try:
            draft = await self.dialogue.generate(
                DialogueRequest(
                    transcript=transcript,
                    lesson=self.lesson,
                    history=self.memory.snapshot(),
                    intent_hint=intent_hint,
                )
            )
            decision = self.policy.apply(recognition, draft)
        except (ProviderError, TimeoutError):
            decision = self.policy.fallback(fallback_intent)
        turn = await self.speech.synthesize(decision.reply_text, decision.reply_locale)
        self.memory.append(
            ConversationTurn(
                learner_text=transcript.text,
                learner_locale=transcript.locale,
                intent=decision.intent,
                teacher_text=decision.reply_text,
                teacher_locale=decision.reply_locale,
            )
        )
        return LessonResult(transcript=transcript, turn=turn)


def build_local_lesson_service(settings: LocalAiSettings) -> LocalLessonService:
    return LocalLessonService(
        recognizer=WhisperCppRecognizer(
            settings.whisper_executable,
            settings.whisper_model,
            timeout_seconds=settings.provider_timeout_seconds,
        ),
        dialogue=LlamaCppDialogueProvider(
            settings.llama_base_url,
            timeout_seconds=max(1.0, settings.provider_timeout_seconds / 2),
            provider_id=settings.dialogue_provider_id,
        ),
        memory_turns=settings.conversation_memory_turns,
    )


def _fallback_intent(text: str, language: str) -> LearnerIntent:
    detected = {
        "en": DetectedLanguage.ENGLISH,
        "bg": DetectedLanguage.BULGARIAN,
        "mixed": DetectedLanguage.MIXED,
    }.get(language, DetectedLanguage.UNKNOWN)
    explicit = classify_explicit_intent(text, detected)
    if explicit is not None:
        return explicit
    if language in {"bg", "mixed"}:
        return LearnerIntent.BULGARIAN_CLARIFICATION
    if language == "en":
        return LearnerIntent.ENGLISH_ANSWER
    return LearnerIntent.AMBIGUOUS


def _tone_wav(frequency_hz: float) -> tuple[bytes, int]:
    sample_rate = 16_000
    duration_seconds = 0.15
    frame_count = int(sample_rate * duration_seconds)
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frame_count):
            fade = min(1.0, index / 160, (frame_count - index) / 160)
            sample = int(5_000 * fade * math.sin(2 * math.pi * frequency_hz * index / sample_rate))
            wav.writeframesraw(struct.pack("<h", sample))
    return output.getvalue(), frame_count * 1_000_000 // sample_rate
