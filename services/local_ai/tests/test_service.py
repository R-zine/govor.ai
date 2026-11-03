from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from govor_contracts import ProviderCapabilities
from govor_domain import DetectedLanguage, DialogueDraft, LearnerIntent, load_lesson_catalog
from govor_local_ai.service import DiagnosticToneSpeechProvider, LocalLessonService
from govor_progress import SQLiteProgressRepository
from govor_provider_interfaces import (
    DialogueRequest,
    NoSpeechRecognized,
    ProviderMalformedOutput,
    ProviderUnavailable,
    Transcript,
    UtteranceAudio,
)


class QueueRecognizer:
    capabilities = ProviderCapabilities(
        provider_id="test-stt",
        provider_kind="speech_recognition",
        local=True,
    )

    def __init__(self, transcripts: list[Transcript]) -> None:
        self.transcripts = transcripts

    async def transcribe(self, audio: UtteranceAudio) -> Transcript:
        assert audio.wav_bytes is not None
        return self.transcripts.pop(0)


class NoSpeechRecognizer:
    capabilities = ProviderCapabilities(
        provider_id="test-stt-no-speech",
        provider_kind="speech_recognition",
        local=True,
    )

    async def transcribe(self, audio: UtteranceAudio) -> Transcript:
        _ = audio
        raise NoSpeechRecognized("silence")


class QueueDialogue:
    capabilities = ProviderCapabilities(
        provider_id="test-dialogue",
        provider_kind="dialogue",
        local=True,
    )

    def __init__(self, drafts: list[DialogueDraft | Exception]) -> None:
        self.drafts = drafts
        self.requests: list[DialogueRequest] = []

    async def generate(self, request: DialogueRequest) -> DialogueDraft:
        self.requests.append(request)
        result = self.drafts.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def transcript(text: str, language: DetectedLanguage) -> Transcript:
    return Transcript(
        text=text,
        locale="bg-BG" if language is DetectedLanguage.BULGARIAN else "en-GB",
        language=language,
        provider_id="test-stt",
    )


def audio() -> UtteranceAudio:
    return UtteranceAudio(uuid4(), 500_000, b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 32)


@pytest.mark.asyncio
async def test_bulgarian_help_then_english_answer_returns_to_english() -> None:
    recognizer = QueueRecognizer(
        [
            transcript("Не разбирам въпроса.", DetectedLanguage.BULGARIAN),
            transcript("I would like coffee, please.", DetectedLanguage.ENGLISH),
        ]
    )
    dialogue = QueueDialogue(
        [
            DialogueDraft(
                LearnerIntent.BULGARIAN_CLARIFICATION,
                "Въпросът е какво искате. Опитайте на английски.",
                "bg-BG",
                True,
            ),
            DialogueDraft(
                LearnerIntent.ENGLISH_ANSWER,
                "Good. Would you like anything else?",
                "en-GB",
                True,
            ),
        ]
    )
    service = LocalLessonService(recognizer, dialogue)

    help_result = await service.respond(audio())
    answer_result = await service.respond(audio())

    assert help_result.turn.locale == "bg-BG"
    assert answer_result.turn.locale == "en-GB"
    assert service.memory.snapshot()[0].intent is LearnerIntent.BULGARIAN_CLARIFICATION
    assert service.memory.snapshot()[1].intent is LearnerIntent.ENGLISH_ANSWER
    assert len(dialogue.requests[1].history) == 1


@pytest.mark.asyncio
async def test_dialogue_failure_uses_deterministic_bilingual_fallback() -> None:
    service = LocalLessonService(
        QueueRecognizer([transcript("Как да кажа искам кафе?", DetectedLanguage.BULGARIAN)]),
        QueueDialogue([ProviderUnavailable("model crashed")]),
    )

    result = await service.respond(audio())

    assert result.turn.locale == "bg-BG"
    assert "I would like" in result.turn.text
    assert service.memory.snapshot()[0].intent is LearnerIntent.BULGARIAN_REFORMULATION


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "accepted"),
    [
        ("Hello, I'd like a cup of tea, please.", True),
        ("I don't want coffee, please.", False),
    ],
)
async def test_model_assessment_controls_success_and_persisted_progress(
    tmp_path, answer: str, accepted: bool
) -> None:  # type: ignore[no-untyped-def]
    dialogue = QueueDialogue(
        [DialogueDraft(LearnerIntent.ENGLISH_ANSWER, "A bounded reply.", "en-GB", accepted)]
    )
    database = tmp_path / "progress.sqlite3"
    service = LocalLessonService(
        QueueRecognizer([transcript(answer, DetectedLanguage.ENGLISH)]),
        dialogue,
        progress_repository=SQLiteProgressRepository(database),
    )
    await service.initial_turn("cafe-ordering")

    await service.respond(audio())

    assert dialogue.requests[0].lesson.teacher_prompt == "What would you like to drink?"
    assert dialogue.requests[0].lesson.objective == "Order a drink politely."
    assert service.progress.successful_exercises == int(accepted)
    assert service.progress.exercise_number == 1 + int(accepted)
    restarted = LocalLessonService(
        QueueRecognizer([]),
        QueueDialogue([]),
        progress_repository=SQLiteProgressRepository(database),
    )
    await restarted.initial_turn("cafe-ordering")
    assert restarted.progress.successful_exercises == int(accepted)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [ProviderUnavailable, ProviderMalformedOutput, TimeoutError])
async def test_unavailable_or_invalid_model_uses_literal_fallback(failure: type[Exception]) -> None:
    service = LocalLessonService(
        QueueRecognizer([transcript("I would like coffee, please.", DetectedLanguage.ENGLISH)]),
        QueueDialogue([failure("unusable assessment")]),
    )

    await service.respond(audio())

    assert service.progress.successful_exercises == 1


@pytest.mark.asyncio
async def test_model_rejection_does_not_use_literal_fallback() -> None:
    service = LocalLessonService(
        QueueRecognizer([transcript("I would like coffee, please.", DetectedLanguage.ENGLISH)]),
        QueueDialogue([DialogueDraft(LearnerIntent.ENGLISH_ANSWER, "Try again.", "en-GB", False)]),
    )

    await service.respond(audio())

    assert service.progress.successful_exercises == 0
    assert service.progress.exercise_number == 1


@pytest.mark.asyncio
async def test_imported_lesson_uses_its_own_question_and_semantic_verdict(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[3] / "assets/lesson-content/cafe-ordering.json"
    lesson = json.loads(source.read_text(encoding="utf-8"))
    lesson["scenario_id"] = "generated-library-lesson"
    lesson["title"] = "Choosing a book"
    exercise = lesson["exercises"][0]
    exercise["goal"] = "Recommend a book to a friend."
    exercise["prompts"] = ["Which book would you recommend?"] * 3
    exercise["accepted_patterns"] = [["I recommend"]]
    lesson["exercises"] = [exercise]
    (tmp_path / "generated.json").write_text(json.dumps(lesson), encoding="utf-8")
    dialogue = QueueDialogue(
        [DialogueDraft(LearnerIntent.ENGLISH_ANSWER, "Good recommendation.", "en-GB", True)]
    )
    service = LocalLessonService(
        QueueRecognizer([transcript("Try reading Treasure Island.", DetectedLanguage.ENGLISH)]),
        dialogue,
        lesson_catalog=load_lesson_catalog(tmp_path),
    )
    await service.initial_turn(lesson["scenario_id"])

    await service.respond(audio())

    assert dialogue.requests[0].lesson.teacher_prompt == "Which book would you recommend?"
    assert dialogue.requests[0].lesson.objective == "Recommend a book to a friend."
    assert service.progress.successful_exercises == 1
    assert service.progress.status.value == "completed"


@pytest.mark.asyncio
async def test_no_speech_asks_for_repeat_without_calling_model_or_storing_memory() -> None:
    dialogue = QueueDialogue([])
    service = LocalLessonService(NoSpeechRecognizer(), dialogue)

    result = await service.respond(audio())

    assert result.transcript is None
    assert result.turn.locale == "bg-BG"
    assert dialogue.requests == []
    assert service.memory.snapshot() == ()


@pytest.mark.asyncio
async def test_diagnostic_audio_is_bounded_and_explicitly_not_speech() -> None:
    provider = DiagnosticToneSpeechProvider()
    turn = await provider.synthesize("Text remains available to Android.", "en-GB")

    assert turn.provider_id == "milestone3-diagnostic-tone"
    assert turn.audio_wav.startswith(b"RIFF")
    assert turn.duration_us == 150_000
    assert "not_speech" in provider.capabilities.features


@pytest.mark.asyncio
async def test_guided_lesson_persists_help_progress_and_completion(tmp_path) -> None:  # type: ignore[no-untyped-def]
    recognizer = QueueRecognizer(
        [
            transcript("Не разбирам.", DetectedLanguage.BULGARIAN),
            transcript("I would like coffee, please.", DetectedLanguage.ENGLISH),
            transcript("That is all, thank you.", DetectedLanguage.ENGLISH),
            transcript("For here, please.", DetectedLanguage.ENGLISH),
        ]
    )
    dialogue = QueueDialogue(
        [
            DialogueDraft(
                LearnerIntent.BULGARIAN_CLARIFICATION,
                "Ще помогна.",
                "bg-BG",
                False,
            ),
            *[
                DialogueDraft(
                    LearnerIntent.ENGLISH_ANSWER,
                    "Good.",
                    "en-GB",
                    True,
                )
                for _ in range(3)
            ],
        ]
    )
    progress = SQLiteProgressRepository(tmp_path / "progress.sqlite3")
    service = LocalLessonService(recognizer, dialogue, progress_repository=progress)
    initial = await service.initial_turn("cafe-ordering")

    assert initial.locale == "en-GB"
    help_result = await service.respond(audio())
    assert help_result.turn.locale == "bg-BG"
    assert service.progress.exercise_number == 1
    for _ in range(3):
        result = await service.respond(audio())

    assert result.turn.text.startswith("Well done.")
    assert service.progress.status.value == "completed"
    history = progress.history()
    assert history["scenarios"][0]["completed_count"] == 1
    assert sum(item["help_requests"] for item in history["exercises"]) == 1

    restarted = LocalLessonService(
        QueueRecognizer([]),
        QueueDialogue([]),
        progress_repository=SQLiteProgressRepository(tmp_path / "progress.sqlite3"),
    )
    next_initial = await restarted.initial_turn("cafe-ordering")
    assert not next_initial.text.startswith("Welcome back.")
