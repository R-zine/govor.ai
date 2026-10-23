import json
import shutil
from pathlib import Path

import httpx
import pytest
from govor_domain import Difficulty, load_lesson_catalog
from govor_local_ai.lesson_creator import (
    GeneratedLessonContent,
    LessonCreationRequest,
    LlamaCppLessonContentProvider,
    ResolvedLessonOptions,
    create_lesson,
    resolve_lesson_options,
)
from govor_provider_interfaces import ProviderMalformedOutput, ProviderUnavailable

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCENES = {"cafe", "supermarket", "airport", "home"}


def _content(exercise_count: int, *, title: str = "Checking in at a hotel") -> dict[str, object]:
    return {
        "title": title,
        "description": "Practise a polite hotel check-in.",
        "objectives": ["Check in and answer a receptionist's questions."],
        "target_vocabulary": ["reservation", "passport", "room"],
        "difficulty_descriptions": [
            "Use modelled check-in phrases.",
            "Answer short follow-up questions.",
            "Handle a natural check-in exchange.",
        ],
        "examples": [
            {
                "teacher": "Do you have a reservation?",
                "learner": "Yes, I have a reservation under Ivanov.",
            }
        ],
        "common_misunderstandings": [
            {
                "pattern": "I have reserve",
                "correction": "Say: I have a reservation.",
                "explanation_bg": "Използвайте съществителното ‘reservation’.",
            }
        ],
        "exercises": [
            {
                "exercise_type": "guided_response",
                "goal": f"Complete hotel step {index}",
                "expected_intent": "answer_receptionist",
                "prompts": [
                    f"Say: I am ready for step {index}.",
                    f"Please complete check-in step {index}.",
                    f"Respond naturally to check-in step {index}.",
                ],
                "accepted_patterns": [["step", str(index)]],
                "target_vocabulary": ["reservation", f"step {index}"],
                "gentle_correction": "Give a complete check-in answer.",
                "explanation_bg": "Отговорете с цяло изречение на английски.",
            }
            for index in range(1, exercise_count + 1)
        ],
        "completion_condition": f"Complete all {exercise_count} hotel exchanges.",
    }


class _RecordingProvider:
    def __init__(self, content: dict[str, object]) -> None:
        self.content = GeneratedLessonContent.model_validate(content)
        self.requests: list[tuple[LessonCreationRequest, ResolvedLessonOptions]] = []

    async def generate(
        self,
        request: LessonCreationRequest,
        options: ResolvedLessonOptions,
    ) -> GeneratedLessonContent:
        self.requests.append((request, options))
        return self.content


def _catalog_directory(tmp_path: Path) -> Path:
    destination = tmp_path / "lessons"
    shutil.copytree(REPOSITORY_ROOT / "assets" / "lesson-content", destination)
    return destination


def test_omitted_generation_options_are_deterministic() -> None:
    request = LessonCreationRequest(topic="Practise ordering coffee")

    first = resolve_lesson_options(request, SCENES)
    second = resolve_lesson_options(request, SCENES)

    assert first == second
    assert first == ResolvedLessonOptions(
        difficulty=Difficulty.INTERMEDIATE,
        scene_template_id="cafe",
        exercise_count=5,
    )


def test_explicit_generation_options_are_preserved() -> None:
    resolved = resolve_lesson_options(
        LessonCreationRequest(
            topic="Discuss a delayed flight",
            difficulty=Difficulty.ADVANCED,
            scene_template_id="airport",
            exercise_count=2,
        ),
        SCENES,
    )

    assert resolved == ResolvedLessonOptions(Difficulty.ADVANCED, "airport", 2)


@pytest.mark.asyncio
async def test_generated_content_is_validated_and_published_to_live_catalog(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    provider = _RecordingProvider(_content(2))

    created = await create_lesson(
        LessonCreationRequest(
            topic="Checking into a hotel",
            difficulty=Difficulty.BEGINNER,
            scene_template_id="home",
            exercise_count=2,
        ),
        provider,
        destination,
        allowed_scene_templates=SCENES,
    )

    assert created.imported.scenario_id == "checking-in-at-a-hotel"
    assert created.options == ResolvedLessonOptions(Difficulty.BEGINNER, "home", 2)
    assert provider.requests[0][1] == created.options
    installed = json.loads(created.imported.destination.read_text(encoding="utf-8"))
    assert installed["scene_template_id"] == "home"
    assert len(installed["exercises"]) == 2
    assert installed["exercises"][0]["exercise_id"] == "complete-hotel-step-1"
    assert load_lesson_catalog(destination).get(created.imported.scenario_id).title == (
        "Checking in at a hotel"
    )


@pytest.mark.asyncio
async def test_repeated_generated_title_gets_an_additive_scenario_id(tmp_path: Path) -> None:
    destination = _catalog_directory(tmp_path)
    request = LessonCreationRequest(topic="Hotel check-in", exercise_count=1)

    first = await create_lesson(
        request,
        _RecordingProvider(_content(1, title="Hotel check-in")),
        destination,
        allowed_scene_templates=SCENES,
    )
    second = await create_lesson(
        request,
        _RecordingProvider(_content(1, title="Hotel check-in")),
        destination,
        allowed_scene_templates=SCENES,
    )

    assert first.imported.scenario_id == "hotel-check-in"
    assert second.imported.scenario_id == "hotel-check-in-2"


@pytest.mark.asyncio
async def test_full_catalog_is_rejected_before_model_generation(tmp_path: Path) -> None:
    destination = tmp_path / "lessons"
    destination.mkdir()
    template = json.loads(
        (REPOSITORY_ROOT / "assets" / "lesson-content" / "cafe-ordering.json").read_text(
            encoding="utf-8"
        )
    )
    for index in range(64):
        lesson = dict(template)
        lesson.update(
            {
                "scenario_id": f"generated-fixture-{index:02d}",
                "title": f"Generated fixture {index}",
                "display_order": index,
            }
        )
        (destination / f"generated-fixture-{index:02d}.json").write_text(
            json.dumps(lesson), encoding="utf-8"
        )
    provider = _RecordingProvider(_content(1))

    with pytest.raises(ValueError, match="maximum of 64"):
        await create_lesson(
            LessonCreationRequest(topic="One more lesson", exercise_count=1),
            provider,
            destination,
            allowed_scene_templates=SCENES,
        )

    assert provider.requests == []


@pytest.mark.asyncio
async def test_llama_provider_sends_bounded_structured_request() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_content(2))}}]},
        )

    provider = LlamaCppLessonContentProvider(
        "http://127.0.0.1:8767",
        max_attempts=1,
        transport=httpx.MockTransport(handler),
    )
    result = await provider.generate(
        LessonCreationRequest(topic="Hotel check-in", exercise_count=2),
        ResolvedLessonOptions(Difficulty.INTERMEDIATE, "home", 2),
    )

    assert len(result.exercises) == 2
    assert seen["seed"] == 42
    assert seen["response_format"]["type"] == "json_schema"  # type: ignore[index]
    messages = seen["messages"]
    assert isinstance(messages, list)
    assert '"required_exercise_count":2' in messages[1]["content"]


@pytest.mark.asyncio
async def test_llama_provider_rejects_wrong_exercise_count() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_content(1))}}]},
        )
    )
    provider = LlamaCppLessonContentProvider(
        "http://localhost:8767",
        max_attempts=1,
        transport=transport,
    )

    with pytest.raises(ProviderMalformedOutput, match="invalid structured"):
        await provider.generate(
            LessonCreationRequest(topic="Hotel check-in", exercise_count=2),
            ResolvedLessonOptions(Difficulty.INTERMEDIATE, "home", 2),
        )


@pytest.mark.asyncio
async def test_llama_provider_retries_only_bounded_transport_failures() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    provider = LlamaCppLessonContentProvider(
        "http://127.0.0.1:8767",
        max_attempts=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderUnavailable):
        await provider.generate(
            LessonCreationRequest(topic="Hotel check-in"),
            ResolvedLessonOptions(Difficulty.INTERMEDIATE, "home", 5),
        )
    assert attempts == 2


def test_lesson_provider_refuses_non_loopback_endpoints() -> None:
    with pytest.raises(ValueError, match="loopback"):
        LlamaCppLessonContentProvider("https://models.example.com")


@pytest.mark.parametrize("count", [0, 9])
def test_lesson_length_is_bounded(count: int) -> None:
    with pytest.raises(ValueError, match="between one and eight"):
        LessonCreationRequest(topic="Hotel", exercise_count=count)
