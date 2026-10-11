"""Strict OpenAI-compatible client for a loopback llama.cpp server."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx
from govor_contracts import ProviderCapabilities
from govor_domain import DialogueDraft, LearnerIntent
from govor_provider_interfaces import (
    DialogueRequest,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StructuredDialogueOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: LearnerIntent
    reply_text: str = Field(min_length=1, max_length=2_048)
    reply_locale: str = Field(pattern=r"^(en-GB|bg-BG)$")
    advance_exercise: bool


DIALOGUE_JSON_SCHEMA: dict[str, Any] = StructuredDialogueOutput.model_json_schema()


class LlamaCppDialogueProvider:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 30.0,
        max_attempts: int = 2,
        provider_id: str = "llama.cpp-qwen3-4b-q4_k_m",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("llama.cpp must use a loopback HTTP endpoint")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("llama.cpp URL must not contain credentials or parameters")
        if not 1 <= max_attempts <= 3:
            raise ValueError("llama.cpp attempts must be between one and three")
        if not provider_id or len(provider_id) > 64:
            raise ValueError("llama.cpp provider id must be non-empty and bounded")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_attempts = max_attempts
        self._transport = transport
        self.capabilities = ProviderCapabilities(
            provider_id=provider_id,
            provider_kind="dialogue",
            local=True,
            features=frozenset(
                {"structured_json", "english", "bulgarian", "mixed_language", "offline"}
            ),
        )

    async def generate(self, request: DialogueRequest) -> DialogueDraft:
        for attempt in range(self._max_attempts):
            try:
                return await self._generate_once(request)
            except (ProviderUnavailable, TimeoutError):
                if attempt + 1 == self._max_attempts:
                    raise
        raise AssertionError("bounded retry loop exited unexpectedly")

    async def _generate_once(self, request: DialogueRequest) -> DialogueDraft:
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _request_prompt(request)},
            ],
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 20,
            "max_tokens": 240,
            "seed": 42,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "govor_dialogue_decision",
                    "strict": True,
                    "schema": DIALOGUE_JSON_SCHEMA,
                },
            },
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/v1/chat/completions",
                    json=payload,
                )
            if response.status_code in {429, 507}:
                raise ProviderResourceExhausted("llama.cpp reported resource exhaustion")
            if response.status_code >= 500:
                raise ProviderUnavailable("llama.cpp failed to generate a response")
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise TimeoutError("llama.cpp generation timed out") from error
        except httpx.HTTPError as error:
            raise ProviderUnavailable("llama.cpp is unavailable") from error

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or len(content) > 16_384:
                raise ValueError("content is not a bounded string")
            parsed = StructuredDialogueOutput.model_validate_json(content)
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as error:
            raise ProviderMalformedOutput("llama.cpp returned invalid structured output") from error
        return DialogueDraft(
            intent=request.intent_hint or parsed.intent,
            reply_text=parsed.reply_text,
            reply_locale=parsed.reply_locale,
            advance_exercise=parsed.advance_exercise,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=min(self._timeout, 2.0),
                transport=self._transport,
            ) as client:
                response = await client.get(f"{self._base_url}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False


def _system_prompt() -> str:
    intents = ", ".join(intent.value for intent in LearnerIntent)
    return f"""You are a patient English teacher for an adult Bulgarian learner.
Return only JSON matching the supplied schema. Never emit application commands, tool calls,
paths, URLs, or markdown. The allowed intent values are: {intents}.
English is the default teaching language. For a Bulgarian clarification or reformulation request,
give concise Bulgarian help, include useful English wording, and invite the learner back to
English. Help, repetition, vocabulary questions, ambiguity, and recognition errors never advance
the exercise. Only a meaningful English answer may set advance_exercise to true.
Classification rules are strict:
- "Как да кажа ...?" is bulgarian_reformulation with reply_locale bg-BG.
- "What does ... mean?" and "Какво означава ...?" are vocabulary_explanation; reply in bg-BG.
- "Не разбирам" or a Bulgarian request to explain is bulgarian_clarification; reply in bg-BG.
- A request to repeat is repeat; a request to speak slowly is slower_speech.
The learner input may contain an intent_hint from a deterministic classifier. When it is not null,
use exactly that intent and its required reply language.
/no_think"""


def _request_prompt(request: DialogueRequest) -> str:
    history = [
        {
            "learner": turn.learner_text,
            "learner_locale": turn.learner_locale,
            "intent": turn.intent.value,
            "teacher": turn.teacher_text,
            "teacher_locale": turn.teacher_locale,
        }
        for turn in request.history
    ]
    data = {
        "lesson": {
            "scenario_id": request.lesson.scenario_id,
            "objective": request.lesson.objective,
            "teacher_prompt": request.lesson.teacher_prompt,
            "target_vocabulary": request.lesson.target_vocabulary,
        },
        "bounded_history": history,
        "learner_utterance": {
            "text": request.transcript.text,
            "locale": request.transcript.locale,
            "language": request.transcript.language.value,
            "intent_hint": request.intent_hint.value if request.intent_hint is not None else None,
        },
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
