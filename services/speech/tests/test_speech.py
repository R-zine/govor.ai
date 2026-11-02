from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from govor_provider_interfaces import ProviderUnavailable
from govor_speech import (
    EspeakFallbackSpeechProvider,
    KokoroEnglishSpeechProvider,
    LocalSpeechRouter,
    PiperBulgarianSpeechProvider,
    build_local_speech_provider,
)
from govor_speech.audio import inspect_wav, pcm16_wav
from govor_speech.phonemes import RawPhonemeTiming, align_to_words, pronunciations_for


class FakeKokoro:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_timed(self, text: str, **kwargs: object) -> tuple[Any, int, list[Any]]:
        self.calls.append({"text": text, **kwargs})
        samples = np.zeros(24_000, dtype=np.float32)
        timings = [
            SimpleNamespace(phoneme="h", start=0.0, end=0.2),
            SimpleNamespace(phoneme="ə", start=0.2, end=0.4),
            SimpleNamespace(phoneme=" ", start=0.4, end=0.5),
            SimpleNamespace(phoneme="w", start=0.5, end=0.7),
            # The upstream float may round one microsecond beyond the trimmed WAV.
            SimpleNamespace(phoneme="ɜ", start=0.7, end=1.000001),
        ]
        return samples, 24_000, timings


class FakePiper:
    def __init__(self) -> None:
        self.configs: list[Any] = []

    def synthesize(self, _text: str, *, syn_config: Any, include_alignments: bool) -> list[Any]:
        assert include_alignments
        self.configs.append(syn_config)
        phonemes = [
            SimpleNamespace(phoneme=symbol, num_samples=1_000)
            for symbol in ("d", "o", " ", "b", "a", "r")
        ]
        return [
            SimpleNamespace(
                sample_rate=22_050,
                sample_width=2,
                sample_channels=1,
                audio_int16_bytes=b"\0\0" * 6_000,
                phoneme_alignments=phonemes,
            )
        ]


@pytest.mark.asyncio
async def test_kokoro_uses_accent_voice_speed_and_actual_timings() -> None:
    engine = FakeKokoro()
    provider = KokoroEnglishSpeechProvider(
        "missing.onnx",
        "missing.bin",
        engine_factory=lambda: engine,
    )

    turn = await provider.synthesize("hello world", "en-GB", speed=0.75)

    assert engine.calls[0]["voice"] == "bf_emma"
    assert engine.calls[0]["lang"] == "en-gb"
    assert engine.calls[0]["speed"] == 0.75
    assert turn.sample_rate_hz == 24_000
    assert turn.duration_us == 1_000_000
    assert [item.word for item in turn.pronunciations] == ["hello", "world"]
    assert turn.word_alignment is not None
    assert turn.word_alignment[1].start_us == 500_000
    assert turn.word_alignment[1].end_us == turn.duration_us
    assert turn.phoneme_alignment is not None
    assert not turn.fallback_used

    await provider.synthesize("hello world", "en-US", speed=1.25)
    assert engine.calls[1]["voice"] == "af_heart"
    assert engine.calls[1]["lang"] == "en-us"


@pytest.mark.asyncio
async def test_kokoro_voice_follows_the_selected_teacher_profile() -> None:
    engine = FakeKokoro()
    selected = "amira"
    provider = KokoroEnglishSpeechProvider(
        "missing.onnx",
        "missing.bin",
        teacher_profile_provider=lambda: selected,
        engine_factory=lambda: engine,
    )

    await provider.synthesize("Welcome.", "en-GB")
    selected = "daniel"
    await provider.synthesize("Welcome.", "en-US")

    assert engine.calls[0]["voice"] == "bf_isabella"
    assert engine.calls[1]["voice"] == "am_michael"


@pytest.mark.asyncio
async def test_piper_uses_speed_and_model_sample_alignment() -> None:
    engine = FakePiper()
    provider = PiperBulgarianSpeechProvider(
        "missing.onnx",
        "missing.json",
        engine_factory=lambda: engine,
    )

    turn = await provider.synthesize("добър ден", "bg-BG", speed=1.25)

    assert engine.configs[0].length_scale == pytest.approx(0.8)
    assert turn.sample_rate_hz == 22_050
    assert [item.word for item in turn.pronunciations] == ["добър", "ден"]
    assert turn.word_alignment is not None
    assert turn.phoneme_alignment is not None
    assert turn.word_alignment[0].start_us == 0
    assert turn.word_alignment[-1].end_us <= turn.duration_us


@pytest.mark.asyncio
async def test_real_espeak_fallback_has_consistent_wav_shape_without_alignment() -> None:
    provider = EspeakFallbackSpeechProvider(timeout_seconds=10.0)

    first = await provider.synthesize("Hello learner.", "en-GB", speed=1.0)
    second = await provider.synthesize("Hello learner.", "en-GB", speed=1.0)
    bulgarian = await provider.synthesize("Добър ден.", "bg-BG", speed=0.75)

    assert inspect_wav(first.audio_wav) == inspect_wav(second.audio_wav)
    assert first.fallback_used
    assert first.word_alignment is None
    assert first.phoneme_alignment is None
    assert first.sample_rate_hz == bulgarian.sample_rate_hz == 22_050
    assert bulgarian.duration_us > first.duration_us / 2


@pytest.mark.asyncio
async def test_router_falls_back_only_when_preferred_is_unavailable() -> None:
    fallback = EspeakFallbackSpeechProvider(timeout_seconds=10.0)

    class BrokenProvider:
        async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> Any:
            raise ProviderUnavailable(f"unavailable: {text} {locale} {speed}")

    router = LocalSpeechRouter(BrokenProvider(), BrokenProvider(), fallback)
    turn = await router.synthesize("Try again.", "en-US", speed=1.25)

    assert turn.fallback_used
    assert turn.provider_id.startswith("espeak-ng-")


@pytest.mark.asyncio
async def test_bulgarian_prefers_neural_piper_for_every_teacher() -> None:
    calls: list[str] = []
    selected = "amira"

    class RecordingProvider:
        def __init__(self, name: str) -> None:
            self.name = name

        async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> Any:
            calls.append(self.name)
            return SimpleNamespace(text=text, locale=locale, speed=speed)

    router = LocalSpeechRouter(
        RecordingProvider("english"),
        RecordingProvider("piper"),
        RecordingProvider("fallback"),
        teacher_profile_provider=lambda: selected,
    )

    await router.synthesize("Добър ден.", "bg-BG")
    selected = "daniel"
    await router.synthesize("Добър ден.", "bg-BG")

    assert calls == ["piper", "piper"]


@pytest.mark.asyncio
async def test_bulgarian_provider_failure_keeps_profile_aware_fallback() -> None:
    calls: list[str] = []

    class BrokenBulgarian:
        async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> Any:
            raise ProviderUnavailable(f"unavailable: {text} {locale} {speed}")

    class RecordingFallback:
        async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> Any:
            calls.append(f"{text}:{locale}:{speed}")
            return SimpleNamespace(text=text, locale=locale, speed=speed)

    router = LocalSpeechRouter(
        BrokenBulgarian(),
        BrokenBulgarian(),
        RecordingFallback(),
        teacher_profile_provider=lambda: "amira",
    )

    await router.synthesize("Добър ден.", "bg-BG")

    assert calls == ["Добър ден.:bg-BG:1.0"]


def test_curated_ipa_is_accent_aware_and_bulgarian_is_not_empty() -> None:
    british = pronunciations_for("water thought schedule", "en-GB")
    american = pronunciations_for("water thought schedule", "en-US")
    bulgarian = pronunciations_for("Добър ден", "bg-BG")

    assert [item.ipa for item in british] == ["wˈɔːtə", "θˈɔːt", "ʃˈɛdjuːl"]
    assert [item.ipa for item in american] == ["wˈɔːɾɚ", "θˈɔːt", "skˈɛdʒuːl"]
    assert [item.ipa for item in bulgarian] == ["dˈobər", "dˈen"]
    assert british[1].explanation is not None
    assert all(item.explanation is None for item in bulgarian)


def test_alignment_is_explicitly_absent_when_provider_groups_do_not_match() -> None:
    timing = (RawPhonemeTiming("h", 0, 100),)

    assert align_to_words((), 1) == (None, None)
    assert align_to_words(timing, 2) == (None, None)
    assert align_to_words((RawPhonemeTiming(".", 0, 100),), 1) == (None, None)


def test_wav_helpers_validate_pcm_and_metadata() -> None:
    wav = pcm16_wav(b"\0\0" * 16_000, 16_000)
    info = inspect_wav(wav)

    assert info.duration_us == 1_000_000
    assert info.channels == 1
    with pytest.raises(ValueError):
        pcm16_wav(b"", 16_000)
    with pytest.raises(ValueError):
        inspect_wav(b"not a wav")


def test_factory_builds_locale_router() -> None:
    settings = SimpleNamespace(
        kokoro_model="kokoro.onnx",
        kokoro_voices="voices.bin",
        kokoro_voice_gb="bf_emma",
        kokoro_voice_us="af_heart",
        piper_bg_model="bg.onnx",
        piper_bg_config="bg.onnx.json",
        provider_timeout_seconds=3.0,
    )

    router = build_local_speech_provider(settings)

    assert isinstance(router.english, KokoroEnglishSpeechProvider)
    assert isinstance(router.bulgarian, PiperBulgarianSpeechProvider)
    assert isinstance(router.fallback, EspeakFallbackSpeechProvider)


@pytest.mark.parametrize(
    ("text", "locale", "speed"),
    [("", "en-GB", 1.0), ("hello", "fr-FR", 1.0), ("hello", "en-GB", 0.25)],
)
@pytest.mark.asyncio
async def test_speech_request_bounds_are_enforced(text: str, locale: str, speed: float) -> None:
    provider = KokoroEnglishSpeechProvider("missing", "missing", engine_factory=FakeKokoro)

    with pytest.raises(ValueError):
        await provider.synthesize(text, locale, speed=speed)
