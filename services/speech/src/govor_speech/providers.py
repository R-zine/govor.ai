"""Offline English/Bulgarian speech synthesis and deterministic fallback."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from govor_contracts import ProviderCapabilities
from govor_provider_interfaces import ProviderUnavailable, SpeechProvider, TeacherTurn

from .audio import inspect_wav, pcm16_wav
from .phonemes import RawPhonemeTiming, align_to_words, pronunciations_for


class SpeechSettings(Protocol):
    kokoro_model: str
    kokoro_voices: str
    kokoro_voice_gb: str
    kokoro_voice_us: str
    piper_bg_model: str
    piper_bg_config: str
    provider_timeout_seconds: float


class KokoroEnglishSpeechProvider:
    capabilities = ProviderCapabilities(
        provider_id="kokoro-onnx-v1.0",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset(
            {
                "natural_english",
                "en-GB",
                "en-US",
                "ipa",
                "phoneme_alignment_when_available",
                "speed",
                "wav_pcm16_mono",
            }
        ),
    )

    def __init__(
        self,
        model_path: str,
        voices_path: str,
        *,
        voice_gb: str = "bf_emma",
        voice_us: str = "af_heart",
        engine_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._model_path = str(Path(model_path).resolve())
        self._voices_path = str(Path(voices_path).resolve())
        self._voice_gb = voice_gb
        self._voice_us = voice_us
        self._engine_factory = engine_factory
        self._engine: Any | None = None

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        return await asyncio.to_thread(self._synthesize, text, locale, speed)

    def _synthesize(self, text: str, locale: str, speed: float) -> TeacherTurn:
        _validate_request(text, locale, speed, allowed_locales={"en-GB", "en-US"})
        engine = self._engine_instance()
        voice = self._voice_gb if locale == "en-GB" else self._voice_us
        language = "en-gb" if locale == "en-GB" else "en-us"
        try:
            samples, sample_rate, timings = engine.create_timed(
                text,
                voice=voice,
                speed=speed,
                lang=language,
                trim=True,
            )
            import numpy as np

            pcm = np.rint(np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
            audio_wav = pcm16_wav(pcm, int(sample_rate))
            duration_us = len(pcm) // 2 * 1_000_000 // int(sample_rate)
            raw_timing_items: list[RawPhonemeTiming] = []
            for item in timings:
                start_us = max(0, min(duration_us, round(float(item.start) * 1_000_000)))
                end_us = max(0, min(duration_us, round(float(item.end) * 1_000_000)))
                if end_us > start_us:
                    raw_timing_items.append(
                        RawPhonemeTiming(
                            symbol=str(item.phoneme),
                            start_us=start_us,
                            end_us=end_us,
                        )
                    )
            raw_timings = tuple(raw_timing_items)
        except Exception as error:
            raise ProviderUnavailable("Kokoro synthesis failed") from error
        return _turn_from_audio(
            text=text,
            locale=locale,
            audio_wav=audio_wav,
            provider_id=self.capabilities.provider_id,
            raw_timings=raw_timings,
        )

    def _engine_instance(self) -> Any:
        if self._engine is None:
            if self._engine_factory is not None:
                self._engine = self._engine_factory()
            else:
                if not Path(self._model_path).is_file() or not Path(self._voices_path).is_file():
                    raise ProviderUnavailable("Kokoro model or voices are missing")
                from kokoro_onnx import Kokoro

                self._engine = Kokoro(self._model_path, self._voices_path)
        return self._engine


class PiperBulgarianSpeechProvider:
    capabilities = ProviderCapabilities(
        provider_id="piper-bg_BG-dimitar-medium",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset(
            {
                "bulgarian",
                "bg-BG",
                "ipa",
                "model_phoneme_alignment",
                "speed",
                "wav_pcm16_mono",
            }
        ),
    )

    def __init__(
        self,
        model_path: str,
        config_path: str,
        *,
        engine_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._model_path = str(Path(model_path).resolve())
        self._config_path = str(Path(config_path).resolve())
        self._engine_factory = engine_factory
        self._engine: Any | None = None

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        return await asyncio.to_thread(self._synthesize, text, locale, speed)

    def _synthesize(self, text: str, locale: str, speed: float) -> TeacherTurn:
        _validate_request(text, locale, speed, allowed_locales={"bg-BG"})
        try:
            from piper.config import SynthesisConfig

            chunks = tuple(
                self._engine_instance().synthesize(
                    text,
                    syn_config=SynthesisConfig(length_scale=1.0 / speed),
                    include_alignments=True,
                )
            )
            if not chunks:
                raise ValueError("Piper returned no audio")
            sample_rate = int(chunks[0].sample_rate)
            if any(
                int(chunk.sample_rate) != sample_rate
                or int(chunk.sample_width) != 2
                or int(chunk.sample_channels) != 1
                for chunk in chunks
            ):
                raise ValueError("Piper returned inconsistent audio chunks")
            pcm = b"".join(bytes(chunk.audio_int16_bytes) for chunk in chunks)
            audio_wav = pcm16_wav(pcm, sample_rate)
            raw_timings = _piper_timings(chunks, sample_rate)
        except Exception as error:
            raise ProviderUnavailable("Piper Bulgarian synthesis failed") from error
        return _turn_from_audio(
            text=text,
            locale=locale,
            audio_wav=audio_wav,
            provider_id=self.capabilities.provider_id,
            raw_timings=raw_timings,
        )

    def _engine_instance(self) -> Any:
        if self._engine is None:
            if self._engine_factory is not None:
                self._engine = self._engine_factory()
            else:
                if not Path(self._model_path).is_file() or not Path(self._config_path).is_file():
                    raise ProviderUnavailable("Piper Bulgarian model or config is missing")
                from piper import PiperVoice

                self._engine = PiperVoice.load(
                    self._model_path,
                    config_path=self._config_path,
                    include_alignments=True,
                )
        return self._engine


class EspeakFallbackSpeechProvider:
    capabilities = ProviderCapabilities(
        provider_id="espeak-ng-1.52-library-fallback",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset(
            {
                "deterministic_fallback",
                "en-GB",
                "en-US",
                "bg-BG",
                "ipa",
                "speed",
                "alignment_unavailable",
                "wav_pcm16_mono",
            }
        ),
    )

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        _validate_request(
            text,
            locale,
            speed,
            allowed_locales={"en-GB", "en-US", "bg-BG"},
        )
        voice = {"en-GB": "en", "en-US": "en-us", "bg-BG": "bg"}[locale]
        rate = round(175 * speed)
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(Path(__file__).with_name("espeak_worker.py")),
            "--voice",
            voice,
            "--rate",
            str(rate),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _stderr = await asyncio.wait_for(
                process.communicate(text.encode("utf-8")),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise ProviderUnavailable("eSpeak NG fallback timed out") from error
        if process.returncode != 0:
            raise ProviderUnavailable("eSpeak NG fallback failed")
        return _turn_from_audio(
            text=text,
            locale=locale,
            audio_wav=stdout,
            provider_id=self.capabilities.provider_id,
            raw_timings=(),
            fallback_used=True,
        )


class LocalSpeechRouter:
    """Locale router with one serialized fallback-safe synthesis boundary."""

    capabilities = ProviderCapabilities(
        provider_id="local-speech-router-v1",
        provider_kind="speech_synthesis",
        local=True,
        features=frozenset(
            {
                "natural_english",
                "bulgarian",
                "deterministic_fallback",
                "en-GB",
                "en-US",
                "bg-BG",
                "ipa",
                "word_alignment_when_available",
                "phoneme_alignment_when_available",
                "word_replay",
                "speed",
                "wav_pcm16_mono",
            }
        ),
    )

    def __init__(
        self,
        english: SpeechProvider,
        bulgarian: SpeechProvider,
        fallback: SpeechProvider,
    ) -> None:
        self.english = english
        self.bulgarian = bulgarian
        self.fallback = fallback
        self._lock = asyncio.Lock()

    async def synthesize(self, text: str, locale: str, *, speed: float = 1.0) -> TeacherTurn:
        preferred = self.bulgarian if locale == "bg-BG" else self.english
        async with self._lock:
            try:
                return await preferred.synthesize(text, locale, speed=speed)
            except (ProviderUnavailable, TimeoutError, OSError, ValueError):
                return await self.fallback.synthesize(text, locale, speed=speed)


def build_local_speech_provider(settings: SpeechSettings) -> LocalSpeechRouter:
    return LocalSpeechRouter(
        english=KokoroEnglishSpeechProvider(
            settings.kokoro_model,
            settings.kokoro_voices,
            voice_gb=settings.kokoro_voice_gb,
            voice_us=settings.kokoro_voice_us,
        ),
        bulgarian=PiperBulgarianSpeechProvider(
            settings.piper_bg_model,
            settings.piper_bg_config,
        ),
        fallback=EspeakFallbackSpeechProvider(
            timeout_seconds=settings.provider_timeout_seconds,
        ),
    )


def _turn_from_audio(
    *,
    text: str,
    locale: str,
    audio_wav: bytes,
    provider_id: str,
    raw_timings: tuple[RawPhonemeTiming, ...],
    fallback_used: bool = False,
) -> TeacherTurn:
    info = inspect_wav(audio_wav)
    pronunciations = pronunciations_for(text, locale)
    words, phonemes = align_to_words(raw_timings, len(pronunciations))
    return TeacherTurn(
        text=text,
        locale=locale,
        audio_wav=audio_wav,
        sample_rate_hz=info.sample_rate_hz,
        duration_us=info.duration_us,
        provider_id=provider_id,
        pronunciations=pronunciations,
        word_alignment=words,
        phoneme_alignment=phonemes,
        fallback_used=fallback_used,
    )


def _piper_timings(chunks: tuple[Any, ...], sample_rate: int) -> tuple[RawPhonemeTiming, ...]:
    output: list[RawPhonemeTiming] = []
    offset_samples = 0
    for chunk in chunks:
        alignments = chunk.phoneme_alignments
        if alignments is None:
            return ()
        for alignment in alignments:
            count = int(alignment.num_samples)
            start = offset_samples
            offset_samples += count
            if count > 0:
                output.append(
                    RawPhonemeTiming(
                        symbol=str(alignment.phoneme),
                        start_us=start * 1_000_000 // sample_rate,
                        end_us=offset_samples * 1_000_000 // sample_rate,
                    )
                )
    return tuple(output)


def _validate_request(
    text: str,
    locale: str,
    speed: float,
    *,
    allowed_locales: set[str],
) -> None:
    if not 1 <= len(text) <= 2_048 or not text.strip():
        raise ValueError("speech text is outside accepted bounds")
    if locale not in allowed_locales:
        raise ValueError(f"unsupported speech locale: {locale}")
    if not 0.5 <= speed <= 2.0:
        raise ValueError("speech speed must be between 0.5 and 2.0")
