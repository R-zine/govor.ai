from __future__ import annotations

from govor_domain import (
    ConversationMemory,
    ConversationTurn,
    DetectedLanguage,
    DialogueDraft,
    DialoguePolicy,
    LearnerIntent,
    Recognition,
    classify_explicit_intent,
    detect_language,
)


def recognition(text: str, language: DetectedLanguage) -> Recognition:
    return Recognition(
        text=text,
        language=language,
        locale="bg-BG" if language is DetectedLanguage.BULGARIAN else "en-GB",
        provider_id="test-recognizer",
    )


def test_help_request_cannot_advance_even_when_model_requests_it() -> None:
    decision = DialoguePolicy().apply(
        recognition("Не разбирам.", DetectedLanguage.BULGARIAN),
        DialogueDraft(
            intent=LearnerIntent.BULGARIAN_CLARIFICATION,
            reply_text="Ще обясня.",
            reply_locale="bg-BG",
            advance_exercise=True,
        ),
    )

    assert decision.intent is LearnerIntent.BULGARIAN_CLARIFICATION
    assert decision.advance_exercise is False


def test_only_english_production_can_advance() -> None:
    policy = DialoguePolicy()
    draft = DialogueDraft(
        intent=LearnerIntent.ENGLISH_ANSWER,
        reply_text="Good answer.",
        reply_locale="en-GB",
        advance_exercise=True,
    )

    assert policy.apply(recognition("Coffee.", DetectedLanguage.ENGLISH), draft).advance_exercise
    assert not policy.apply(
        recognition("Кафе.", DetectedLanguage.BULGARIAN), draft
    ).advance_exercise


def test_bulgarian_answer_is_redirected_to_english_reformulation() -> None:
    decision = DialoguePolicy().apply(
        recognition("Искам кафе, моля.", DetectedLanguage.BULGARIAN),
        DialogueDraft(
            intent=LearnerIntent.ENGLISH_ANSWER,
            reply_text="Thank you.",
            reply_locale="en-GB",
            advance_exercise=True,
        ),
    )

    assert decision.intent is LearnerIntent.BULGARIAN_REFORMULATION
    assert decision.reply_locale == "bg-BG"
    assert not decision.advance_exercise


def test_empty_recognition_uses_bulgarian_retry_without_progress() -> None:
    decision = DialoguePolicy().apply(
        recognition("", DetectedLanguage.UNKNOWN),
        DialogueDraft(
            intent=LearnerIntent.ENGLISH_ANSWER,
            reply_text="Incorrect draft.",
            reply_locale="en-GB",
            advance_exercise=True,
        ),
    )

    assert decision.intent is LearnerIntent.RECOGNITION_ERROR
    assert decision.reply_locale == "bg-BG"
    assert not decision.advance_exercise


def test_language_detection_distinguishes_english_bulgarian_and_mixed() -> None:
    assert detect_language("coffee please") is DetectedLanguage.ENGLISH
    assert detect_language("кафе моля") is DetectedLanguage.BULGARIAN
    assert detect_language("кафе please") is DetectedLanguage.MIXED
    assert detect_language("123") is DetectedLanguage.UNKNOWN


def test_explicit_bilingual_help_intents_are_deterministic() -> None:
    assert (
        classify_explicit_intent("Как да кажа coffee?", DetectedLanguage.MIXED)
        is LearnerIntent.BULGARIAN_REFORMULATION
    )
    assert (
        classify_explicit_intent("What does order mean?", DetectedLanguage.ENGLISH)
        is LearnerIntent.VOCABULARY_EXPLANATION
    )
    assert (
        classify_explicit_intent("Може ли по-бавно?", DetectedLanguage.BULGARIAN)
        is LearnerIntent.SLOWER_SPEECH
    )
    assert classify_explicit_intent("Coffee, please.", DetectedLanguage.ENGLISH) is None


def test_conversation_memory_is_bounded_and_clearable() -> None:
    memory = ConversationMemory(max_turns=2)
    for index in range(3):
        memory.append(
            ConversationTurn(
                learner_text=f"learner {index}",
                learner_locale="en-GB",
                intent=LearnerIntent.ENGLISH_ANSWER,
                teacher_text=f"teacher {index}",
                teacher_locale="en-GB",
            )
        )

    assert [turn.learner_text for turn in memory.snapshot()] == ["learner 1", "learner 2"]
    memory.clear()
    assert memory.snapshot() == ()
