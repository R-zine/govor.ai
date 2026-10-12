"""Composition of local recognition, structured dialogue, policy, and temporary audio."""

from __future__ import annotations

import io
import math
import struct
import wave
from dataclasses import replace
from typing import Protocol

from govor_contracts import ProviderCapabilities
from govor_domain import (
    ConversationMemory,
    ConversationTurn,
    DetectedLanguage,
    DialoguePolicy,
    LearnerIntent,
    LearnerSettings,
    LessonProgress,
    Recognition,
    TeachingEngine,
    TeachingOutcome,
    TeachingState,
    classify_explicit_intent,
    get_scenario,
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
    kokoro_model: str
    kokoro_voices: str
    kokoro_voice_gb: str
    kokoro_voice_us: str
    piper_bg_model: str
    piper_bg_config: str
    progress_database: str


class ProgressRepository(Protocol):
    def get_settings(self) -> LearnerSettings: ...

    def update_settings(self, settings: LearnerSettings) -> None: ...

    def load_or_start(self, scenario_id: str) -> tuple[TeachingState, bool]: ...

    def record_outcome(self, outcome: TeachingOutcome, state: TeachingState) -> None: ...


class EphemeralProgressRepository:
    """Non-persistent repository for focused adapter tests only."""

    def __init__(self) -> None:
        self.settings = LearnerSettings()
        self.states: dict[str, TeachingState] = {}

    def get_settings(self) -> LearnerSettings:
        return self.settings

    def update_settings(self, settings: LearnerSettings) -> None:
        self.settings = settings

    def load_or_start(self, scenario_id: str) -> tuple[TeachingState, bool]:
        state = self.states.get(scenario_id)
        if state is None or state.status.value == "completed":
            state = TeachingState(difficulty=self.settings.starting_difficulty)
            self.states[scenario_id] = state
            return state, False
        return state, True

    def record_outcome(self, outcome: TeachingOutcome, state: TeachingState) -> None:
        self.states[outcome.progress.scenario_id] = state


class DiagnosticToneSpeechProvider:
    """Temporary audible transport marker; Milestone 4 replaces it with real speech."""

    capabilities = ProviderCapabilities(
        provider_id="milestone3-diagnostic-tone",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset({"development_only", "not_speech", "wav"}),
    )

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        _ = speed
        audio, duration_us = _tone_wav(440.0 if locale == "en-GB" else 392.0)
        return TeacherTurn(
            text=text,
            locale=locale,
            audio_wav=audio,
            sample_rate_hz=16_000,
            duration_us=duration_us,
            provider_id="milestone3-diagnostic-tone",
        )


class LocalLessonService:
    def __init__(
        self,
        recognizer: SpeechRecognizer,
        dialogue: DialogueProvider,
        speech: SpeechProvider | None = None,
        progress_repository: ProgressRepository | None = None,
        *,
        memory_turns: int = 8,
    ) -> None:
        self.recognizer = recognizer
        self.dialogue = dialogue
        self.speech = speech or DiagnosticToneSpeechProvider()
        self.memory = ConversationMemory(max_turns=memory_turns)
        self.policy = DialoguePolicy()
        self.progress_repository = progress_repository or EphemeralProgressRepository()
        self._engine = TeachingEngine(get_scenario("cafe-ordering"))

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
        settings = self.progress_repository.get_settings()
        self.progress_repository.update_settings(
            replace(
                settings,
                english_locale=english_locale,
                spaced_review_enabled=spaced_review_enabled,
            )
        )
        state, resumed = self.progress_repository.load_or_start(scenario_id)
        self._engine = TeachingEngine(
            get_scenario(scenario_id),
            state,
            resumed=resumed,
            english_locale=english_locale,
        )
        return await self.speech.synthesize(self._engine.initial_prompt(), english_locale)

    async def replay_word(self, word: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        return await self.speech.synthesize(word, locale, speed=speed)

    async def respond(self, audio: UtteranceAudio) -> LessonResult:
        try:
            transcript = await self.recognizer.transcribe(audio)
        except NoSpeechRecognized:
            outcome = self._engine.no_speech()
            turn = await self.speech.synthesize(outcome.reply_text, outcome.reply_locale)
            self.progress_repository.record_outcome(outcome, self._engine.state)
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
                    lesson=self._engine.context(),
                    history=self.memory.snapshot(),
                    intent_hint=intent_hint,
                )
            )
            decision = self.policy.apply(recognition, draft)
        except (ProviderError, TimeoutError):
            decision = self.policy.fallback(fallback_intent)
        outcome = self._engine.evaluate(
            transcript.text,
            transcript.language,
            decision.intent,
        )
        turn = await self.speech.synthesize(outcome.reply_text, outcome.reply_locale)
        self.progress_repository.record_outcome(outcome, self._engine.state)
        self.memory.append(
            ConversationTurn(
                learner_text=transcript.text,
                learner_locale=transcript.locale,
                intent=decision.intent,
                teacher_text=outcome.reply_text,
                teacher_locale=outcome.reply_locale,
            )
        )
        return LessonResult(transcript=transcript, turn=turn)


def build_local_lesson_service(settings: LocalAiSettings) -> LocalLessonService:
    from govor_progress import SQLiteProgressRepository
    from govor_speech import build_local_speech_provider

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
        speech=build_local_speech_provider(settings),
        progress_repository=SQLiteProgressRepository(settings.progress_database),
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
