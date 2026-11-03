"""Strict OpenAI-compatible client for a loopback llama.cpp server."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from govor_contracts import ProviderCapabilities
from govor_domain import DialogueDraft
from govor_provider_interfaces import (
    DIALOGUE_JSON_SCHEMA,
    DialogueRequest,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
    dialogue_messages,
    parse_dialogue_content,
)


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
            "messages": dialogue_messages(request),
            "temperature": 0.0,
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
            return parse_dialogue_content(content, request)
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as error:
            raise ProviderMalformedOutput("llama.cpp returned invalid structured output") from error

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
