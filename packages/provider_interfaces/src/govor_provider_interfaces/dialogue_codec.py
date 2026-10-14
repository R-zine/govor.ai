"""Provider-neutral structured dialogue request and response codec."""

from __future__ import annotations

import json
from typing import Any

from govor_domain import DialogueDraft, LearnerIntent
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .models import DialogueRequest, ProviderMalformedOutput


class StructuredDialogueOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: LearnerIntent
    reply_text: str = Field(min_length=1, max_length=2_048)
    reply_locale: str = Field(pattern=r"^(en-GB|bg-BG)$")
    advance_exercise: bool


DIALOGUE_JSON_SCHEMA: dict[str, Any] = StructuredDialogueOutput.model_json_schema()


def dialogue_messages(request: DialogueRequest) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": _request_prompt(request)},
    ]


def parse_dialogue_content(content: object, request: DialogueRequest) -> DialogueDraft:
    try:
        if not isinstance(content, str) or len(content) > 16_384:
            raise ValueError("content is not a bounded string")
        parsed = StructuredDialogueOutput.model_validate_json(content)
    except (ValueError, json.JSONDecodeError, ValidationError) as error:
        raise ProviderMalformedOutput("provider returned invalid structured dialogue") from error
    return DialogueDraft(
        intent=request.intent_hint or parsed.intent,
        reply_text=parsed.reply_text,
        reply_locale=parsed.reply_locale,
        advance_exercise=parsed.advance_exercise,
    )


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
    data = {
        "lesson": {
            "scenario_id": request.lesson.scenario_id,
            "objective": request.lesson.objective,
            "teacher_prompt": request.lesson.teacher_prompt,
            "target_vocabulary": request.lesson.target_vocabulary,
        },
        "bounded_history": [
            {
                "learner": turn.learner_text,
                "learner_locale": turn.learner_locale,
                "intent": turn.intent.value,
                "teacher": turn.teacher_text,
                "teacher_locale": turn.teacher_locale,
            }
            for turn in request.history
        ],
        "learner_utterance": {
            "text": request.transcript.text,
            "locale": request.transcript.locale,
            "language": request.transcript.language.value,
            "intent_hint": request.intent_hint.value if request.intent_hint is not None else None,
        },
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
