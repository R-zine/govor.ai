"""Execute real local model fixtures and emit machine-readable measurements."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from uuid import uuid4

from govor_domain import (
    CAFE_LESSON,
    DetectedLanguage,
    DialoguePolicy,
    Difficulty,
    Recognition,
    TeachingEngine,
    TeachingState,
    classify_explicit_intent,
    load_lesson_catalog,
)
from govor_local_ai.llama_cpp import LlamaCppDialogueProvider
from govor_local_ai.whisper_cpp import WhisperCppRecognizer
from govor_provider_interfaces import DialogueRequest, Transcript, UtteranceAudio


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-url", default="http://127.0.0.1:8767")
    parser.add_argument("--whisper-executable", required=True)
    parser.add_argument("--whisper-model", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-id", default="qwen3-4b-q4_k_m")
    parser.add_argument("--dialogue-only", action="store_true")
    parser.add_argument(
        "--audio-fixture",
        action="append",
        default=[],
        metavar="ID|PATH|EXPECTED_LANGUAGE|EXPECTED_TEXT_FRAGMENT",
    )
    return parser.parse_args()


async def main() -> int:
    arguments = parse_arguments()
    dialogue_results = await run_dialogue(arguments)
    recognition_results = (
        {"skipped": True, "reason": "model-candidate comparison measures dialogue only"}
        if arguments.dialogue_only
        else await run_recognition(arguments)
    )
    output = {
        "schema_version": "1.0",
        "result_kind": "local_ai_benchmark",
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dialogue": dialogue_results,
        "recognition": recognition_results,
        "privacy": {
            "cloud_requests": 0,
            "recordings_retained": 0,
            "full_transcripts_recorded": False,
        },
    }
    Path(arguments.output).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    dialogue_passed = all(result["passed"] for result in dialogue_results["cases"])
    recognition_cases = recognition_results.get("cases", [])
    recognition_passed = arguments.dialogue_only or (
        bool(recognition_cases) and all(result["passed"] for result in recognition_cases)
    )
    return 0 if dialogue_passed and recognition_passed else 1


async def run_dialogue(arguments: argparse.Namespace) -> dict[str, object]:
    fixtures = json.loads(Path(arguments.fixtures).read_text(encoding="utf-8"))
    catalog = load_lesson_catalog(Path(__file__).resolve().parents[1] / "assets/lesson-content")
    provider = LlamaCppDialogueProvider(arguments.llama_url, timeout_seconds=60.0)
    cases: list[dict[str, object]] = []
    latencies: list[float] = []
    for fixture in fixtures:
        language = DetectedLanguage(fixture["language"])
        engine = (
            TeachingEngine(
                catalog.get(fixture["scenario_id"]),
                TeachingState(
                    exercise_index=fixture.get("exercise_index", 0),
                    difficulty=Difficulty(fixture.get("difficulty", "intermediate")),
                ),
            )
            if "scenario_id" in fixture
            else None
        )
        request = DialogueRequest(
            transcript=Transcript(
                text=fixture["text"],
                locale="bg-BG" if language is DetectedLanguage.BULGARIAN else "en-GB",
                language=language,
                provider_id="benchmark-fixture",
            ),
            lesson=engine.context() if engine is not None else CAFE_LESSON,
            history=(),
            intent_hint=classify_explicit_intent(fixture["text"], language),
        )
        started = time.perf_counter()
        draft = await provider.generate(request)
        output = DialoguePolicy().apply(
            Recognition(
                text=fixture["text"],
                language=language,
                locale=request.transcript.locale,
                provider_id="benchmark-fixture",
            ),
            draft,
        )
        latency_ms = (time.perf_counter() - started) * 1_000
        latencies.append(latency_ms)
        successful = (
            engine.evaluate(
                fixture["text"], language, output.intent, answer_accepted=output.advance_exercise
            ).successful
            is True
            if engine is not None
            else output.advance_exercise
        )
        passed = (
            ("intent" not in fixture or output.intent.value == fixture["intent"])
            and ("reply_locale" not in fixture or output.reply_locale == fixture["reply_locale"])
            and successful == bool(fixture["may_advance"])
        )
        cases.append(
            {
                "id": fixture["id"],
                "passed": passed,
                "expected_intent": fixture.get("intent"),
                "actual_intent": output.intent.value,
                "expected_reply_locale": fixture.get("reply_locale"),
                "actual_reply_locale": output.reply_locale,
                "advance_exercise": output.advance_exercise,
                "exercise_successful": successful,
                "structured_output_valid": True,
                "policy_modified_output": (
                    output.intent != draft.intent
                    or output.reply_locale != draft.reply_locale
                    or output.reply_text != draft.reply_text
                    or output.advance_exercise != draft.advance_exercise
                ),
                "latency_ms": round(latency_ms, 1),
            }
        )
    return {
        "provider_id": arguments.model_id,
        "case_count": len(cases),
        "passed_count": sum(1 for case in cases if case["passed"]),
        "latency_ms_median": round(statistics.median(latencies), 1),
        "latency_ms_max": round(max(latencies), 1),
        "cases": cases,
    }


async def run_recognition(arguments: argparse.Namespace) -> dict[str, object]:
    provider = WhisperCppRecognizer(
        arguments.whisper_executable,
        arguments.whisper_model,
        timeout_seconds=60.0,
    )
    cases: list[dict[str, object]] = []
    latencies: list[float] = []
    for descriptor in arguments.audio_fixture:
        fixture_id, path_value, expected_language, expected_fragment = descriptor.split("|", 3)
        if "\\u" in expected_fragment:
            expected_fragment = expected_fragment.encode("ascii").decode("unicode_escape")
        path = Path(path_value)
        wav = path.read_bytes()
        started = time.perf_counter()
        output = await provider.transcribe(
            UtteranceAudio(
                utterance_id=uuid4(),
                duration_us=_wav_duration_us(wav),
                wav_bytes=wav,
            )
        )
        latency_ms = (time.perf_counter() - started) * 1_000
        latencies.append(latency_ms)
        expected_words = {word.casefold() for word in expected_fragment.split()}
        actual_words = {word.strip(".,!?;:").casefold() for word in output.text.split()}
        passed = output.language.value == expected_language and expected_words <= actual_words
        cases.append(
            {
                "id": fixture_id,
                "passed": passed,
                "detected_language": output.language.value,
                "expected_language": expected_language,
                "expected_words_present": expected_words <= actual_words,
                "audio_bytes": len(wav),
                "duration_us": _wav_duration_us(wav),
                "latency_ms": round(latency_ms, 1),
            }
        )
    return {
        "provider_id": provider.capabilities.provider_id,
        "case_count": len(cases),
        "passed_count": sum(1 for case in cases if case["passed"]),
        "latency_ms_median": round(statistics.median(latencies), 1) if latencies else None,
        "latency_ms_max": round(max(latencies), 1) if latencies else None,
        "cases": cases,
    }


def _wav_duration_us(wav: bytes) -> int:
    import io
    import wave

    with wave.open(io.BytesIO(wav), "rb") as stream:
        return max(1, stream.getnframes() * 1_000_000 // stream.getframerate())


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
