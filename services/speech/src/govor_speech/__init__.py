"""Offline speech adapters for govor.ai."""

from .providers import (
    EspeakFallbackSpeechProvider,
    KokoroEnglishSpeechProvider,
    LocalSpeechRouter,
    PiperBulgarianSpeechProvider,
    build_local_speech_provider,
)

__all__ = [
    "EspeakFallbackSpeechProvider",
    "KokoroEnglishSpeechProvider",
    "LocalSpeechRouter",
    "PiperBulgarianSpeechProvider",
    "build_local_speech_provider",
]
