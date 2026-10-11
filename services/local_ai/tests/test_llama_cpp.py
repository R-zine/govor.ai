from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from govor_domain import CAFE_LESSON, DetectedLanguage, LearnerIntent, classify_explicit_intent
from govor_local_ai.llama_cpp import LlamaCppDialogueProvider
from govor_provider_interfaces import (
    DialogueRequest,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
    Transcript,
)

ROOT = Path(__file__).resolve().parents[3]


def dialogue_request(text: str, language: DetectedLanguage) -> DialogueRequest:
    return DialogueRequest(
        transcript=Transcript(
            text=text,
            locale="bg-BG" if language is DetectedLanguage.BULGARIAN else "en-GB",
            language=language,
            provider_id="fixture-stt",
        ),
        lesson=CAFE_LESSON,
        history=(),
        intent_hint=classify_explicit_intent(text, language),
    )


def completion(content: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={"choices": [{"message": {"content": content}}]},
    )


@pytest.mark.asyncio
async def test_curated_bilingual_fixtures_produce_closed_structured_output() -> None:
    fixtures = json.loads(
        (ROOT / "tests/fixtures/ai/bilingual-cases.json").read_text(encoding="utf-8")
    )
    cases = {case["text"]: case for case in fixtures}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        prompt = json.loads(body["messages"][1]["content"])
        text = prompt["learner_utterance"]["text"]
        case = cases[text]
        return completion(
            json.dumps(
                {
                    "intent": case["intent"],
                    "reply_text": "A bounded teaching response.",
                    "reply_locale": case["reply_locale"],
                    "advance_exercise": case["may_advance"],
                }
            )
        )

    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        transport=httpx.MockTransport(handler),
    )
    for case in fixtures:
        result = await provider.generate(
            dialogue_request(case["text"], DetectedLanguage(case["language"]))
        )
        assert result.intent is LearnerIntent(case["intent"])
        assert result.reply_locale == case["reply_locale"]
        assert result.advance_exercise is case["may_advance"]


@pytest.mark.asyncio
async def test_model_cannot_add_application_control_fields() -> None:
    invalid = json.dumps(
        {
            "intent": "english_answer",
            "reply_text": "Accepted text",
            "reply_locale": "en-GB",
            "advance_exercise": True,
            "renderer_action": "load_arbitrary_path",
        }
    )
    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        transport=httpx.MockTransport(lambda _: completion(invalid)),
    )

    with pytest.raises(ProviderMalformedOutput):
        await provider.generate(dialogue_request("Coffee, please.", DetectedLanguage.ENGLISH))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (429, ProviderResourceExhausted),
        (507, ProviderResourceExhausted),
        (503, ProviderUnavailable),
    ],
)
async def test_resource_and_server_failures_are_typed(
    status_code: int, error_type: type[Exception]
) -> None:
    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        transport=httpx.MockTransport(lambda _: httpx.Response(status_code)),
    )

    with pytest.raises(error_type):
        await provider.generate(dialogue_request("Coffee, please.", DetectedLanguage.ENGLISH))


@pytest.mark.asyncio
async def test_timeout_is_reported_without_untrusted_detail() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private provider detail", request=request)

    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        transport=httpx.MockTransport(timeout),
    )

    with pytest.raises(TimeoutError, match="generation timed out"):
        await provider.generate(dialogue_request("Coffee, please.", DetectedLanguage.ENGLISH))


@pytest.mark.asyncio
async def test_transient_server_failure_is_retried_once() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(503)
        return completion(
            json.dumps(
                {
                    "intent": "english_answer",
                    "reply_text": "Would you like anything else?",
                    "reply_locale": "en-GB",
                    "advance_exercise": True,
                }
            )
        )

    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        transport=httpx.MockTransport(handler),
    )

    result = await provider.generate(dialogue_request("Coffee, please.", DetectedLanguage.ENGLISH))

    assert result.intent is LearnerIntent.ENGLISH_ANSWER
    assert request_count == 2


@pytest.mark.asyncio
async def test_malformed_model_json_is_rejected() -> None:
    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        transport=httpx.MockTransport(lambda _: completion("not-json")),
    )

    with pytest.raises(ProviderMalformedOutput):
        await provider.generate(dialogue_request("Coffee, please.", DetectedLanguage.ENGLISH))


def test_non_loopback_model_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="loopback"):
        LlamaCppDialogueProvider("https://models.example.com")


def test_provider_identity_is_configurable_and_bounded() -> None:
    provider = LlamaCppDialogueProvider(
        "http://127.0.0.1:8767",
        provider_id="llama.cpp-alternate-local-model",
    )

    assert provider.capabilities.provider_id == "llama.cpp-alternate-local-model"
    with pytest.raises(ValueError, match="provider id"):
        LlamaCppDialogueProvider("http://127.0.0.1:8767", provider_id="")
