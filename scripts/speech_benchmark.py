from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import time
import wave
from array import array
from pathlib import Path
from typing import Any

from govor_speech import (
    EspeakFallbackSpeechProvider,
    KokoroEnglishSpeechProvider,
    PiperBulgarianSpeechProvider,
)
from govor_speech.phonemes import pronunciations_for


async def measure(
    provider: Any,
    *,
    name: str,
    text: str,
    locale: str,
    speed: float,
    sample_path: Path | None = None,
) -> tuple[dict[str, object], bytes]:
    started = time.perf_counter()
    turn = await provider.synthesize(text, locale, speed=speed)
    latency_ms = (time.perf_counter() - started) * 1_000
    samples = _wav_samples(turn.audio_wav)
    if not samples or max(abs(value) for value in samples) == 0:
        raise RuntimeError(f"{name} returned silent audio")
    if sample_path is not None:
        sample_path.write_bytes(turn.audio_wav)
    return (
        {
            "name": name,
            "provider_id": turn.provider_id,
            "locale": locale,
            "speed": speed,
            "latency_ms": round(latency_ms, 1),
            "duration_us": turn.duration_us,
            "sample_rate_hz": turn.sample_rate_hz,
            "wav_bytes": len(turn.audio_wav),
            "wav_sha256": hashlib.sha256(turn.audio_wav).hexdigest(),
            "peak_pcm16": max(abs(value) for value in samples),
            "pronunciation_count": len(turn.pronunciations),
            "word_alignment_count": (
                None if turn.word_alignment is None else len(turn.word_alignment)
            ),
            "phoneme_alignment_count": (
                None if turn.phoneme_alignment is None else len(turn.phoneme_alignment)
            ),
            "fallback_used": turn.fallback_used,
        },
        turn.audio_wav,
    )


def _wav_samples(value: bytes) -> array[int]:
    import io

    with wave.open(io.BytesIO(value), "rb") as input_wav:
        if input_wav.getnchannels() != 1 or input_wav.getsampwidth() != 2:
            raise RuntimeError("benchmark received non-mono/non-PCM16 audio")
        samples = array("h")
        samples.frombytes(input_wav.readframes(input_wav.getnframes()))
        return samples


def _assert_speed_order(measurements: list[dict[str, object]], prefix: str) -> None:
    durations = {
        float(item["speed"]): int(item["duration_us"])
        for item in measurements
        if str(item["name"]).startswith(prefix)
    }
    if not durations[0.75] > durations[1.0] > durations[1.25]:
        raise RuntimeError(f"{prefix} speed did not monotonically change audio duration")


async def run(args: argparse.Namespace) -> dict[str, object]:
    sample_root = Path(args.sample_directory)
    sample_root.mkdir(parents=True, exist_ok=True)
    english = KokoroEnglishSpeechProvider(args.kokoro_model, args.kokoro_voices)
    bulgarian = PiperBulgarianSpeechProvider(args.piper_model, args.piper_config)
    fallback = EspeakFallbackSpeechProvider(timeout_seconds=30.0)
    measurements: list[dict[str, object]] = []

    for speed in (0.75, 1.0, 1.25):
        item, _ = await measure(
            english,
            name=f"kokoro-en-gb-{speed}",
            text="Welcome. What would you like to order?",
            locale="en-GB",
            speed=speed,
            sample_path=sample_root / "kokoro-en-gb.wav" if speed == 1.0 else None,
        )
        measurements.append(item)
    item, _ = await measure(
        english,
        name="kokoro-en-us-1.0",
        text="Could I have a coffee, please?",
        locale="en-US",
        speed=1.0,
        sample_path=sample_root / "kokoro-en-us.wav",
    )
    measurements.append(item)
    for speed in (0.75, 1.0, 1.25):
        item, _ = await measure(
            bulgarian,
            name=f"piper-bg-bg-{speed}",
            text="Добър ден. Какво бихте желали?",
            locale="bg-BG",
            speed=speed,
            sample_path=sample_root / "piper-bg-bg.wav" if speed == 1.0 else None,
        )
        measurements.append(item)
    fallback_item, fallback_audio = await measure(
        fallback,
        name="espeak-fallback-en-gb-1.0",
        text="Please try again.",
        locale="en-GB",
        speed=1.0,
        sample_path=sample_root / "espeak-fallback-en-gb.wav",
    )
    repeated = await fallback.synthesize("Please try again.", "en-GB", speed=1.0)
    fallback_item["deterministic_repeat"] = repeated.audio_wav == fallback_audio
    if not fallback_item["deterministic_repeat"]:
        raise RuntimeError("eSpeak fallback did not reproduce identical WAV bytes")
    measurements.append(fallback_item)

    _assert_speed_order(measurements, "kokoro-en-gb")
    _assert_speed_order(measurements, "piper-bg-bg")
    timed_providers = ("kokoro-en-gb-1.0", "piper-bg-bg-1.0")
    for provider_name in timed_providers:
        provider_result = next(item for item in measurements if item["name"] == provider_name)
        if (
            not provider_result["word_alignment_count"]
            or not provider_result["phoneme_alignment_count"]
        ):
            raise RuntimeError(f"{provider_name} did not produce usable model timing")
    if (
        fallback_item["word_alignment_count"] is not None
        or fallback_item["phoneme_alignment_count"] is not None
        or not fallback_item["fallback_used"]
    ):
        raise RuntimeError("fallback timing/identity was not explicitly unavailable")

    british = pronunciations_for("water thought schedule", "en-GB")
    american = pronunciations_for("water thought schedule", "en-US")
    bulgarian_ipa = pronunciations_for("Добър ден", "bg-BG")
    ipa_regression = {
        "en-GB": [item.ipa for item in british],
        "en-US": [item.ipa for item in american],
        "bg-BG": [item.ipa for item in bulgarian_ipa],
    }
    expected_ipa = {
        "en-GB": ["wˈɔːtə", "θˈɔːt", "ʃˈɛdjuːl"],
        "en-US": ["wˈɔːɾɚ", "θˈɔːt", "skˈɛdʒuːl"],
        "bg-BG": ["dˈobər", "dˈen"],
    }
    if ipa_regression != expected_ipa:
        raise RuntimeError("curated IPA regression changed")

    return {
        "schema_version": "1.0",
        "result_kind": "local_speech_benchmark",
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "measurements": measurements,
        "ipa_regression": ipa_regression,
        "sample_directory": str(sample_root.resolve()),
        "manual_listening": "not_executed_by_automated_benchmark",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kokoro-model", required=True)
    parser.add_argument("--kokoro-voices", required=True)
    parser.add_argument("--piper-model", required=True)
    parser.add_argument("--piper-config", required=True)
    parser.add_argument("--sample-directory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = asyncio.run(run(args))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Speech benchmark passed. Results: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
