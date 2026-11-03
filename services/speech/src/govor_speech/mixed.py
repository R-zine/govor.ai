"""Script-aware routing and PCM composition for English/Bulgarian teaching replies."""

from __future__ import annotations

import io
import math
import re
import wave
from dataclasses import dataclass, replace

from govor_provider_interfaces import PhonemeAlignment, Pronunciation, TeacherTurn, WordAlignment

from .audio import inspect_wav, pcm16_wav


@dataclass(frozen=True)
class SpeechSpan:
    start: int
    text: str
    locale: str


def speech_spans(text: str, english_locale: str) -> tuple[SpeechSpan, ...]:
    """Assign neutral punctuation/spacing to the preceding script, preserving source offsets."""

    letters = list(re.finditer(r"[A-Za-z\u00c0-\u024f\u0400-\u04ff]+", text))
    if not letters:
        return (SpeechSpan(0, text, english_locale),)
    start = 0
    locale = "bg-BG" if "\u0400" <= letters[0][0][0] <= "\u04ff" else english_locale
    spans: list[SpeechSpan] = []
    for match in letters[1:]:
        following = "bg-BG" if "\u0400" <= match[0][0] <= "\u04ff" else english_locale
        if following != locale:
            spans.append(SpeechSpan(start, text[start : match.start()], locale))
            start, locale = match.start(), following
    spans.append(SpeechSpan(start, text[start:], locale))
    return tuple(spans)


def combine_turns(
    text: str, locale: str, parts: list[tuple[SpeechSpan, TeacherTurn]]
) -> TeacherTurn:
    """Resample real audio and offset real metadata; missing timing stays unavailable."""

    import numpy as np

    sample_rate = 24_000
    pcm_parts: list[bytes] = []
    pronunciations: list[Pronunciation] = []
    words: list[WordAlignment] = []
    phonemes: list[PhonemeAlignment] = []
    frame_offset = 0
    for span, turn in parts:
        info = inspect_wav(turn.audio_wav)
        with wave.open(io.BytesIO(turn.audio_wav), "rb") as wav:
            samples = np.frombuffer(wav.readframes(info.frame_count), dtype="<i2")
        frames = max(1, math.ceil(len(samples) * sample_rate / info.sample_rate_hz))
        positions = np.arange(frames) * info.sample_rate_hz / sample_rate
        pcm = np.rint(np.interp(positions, np.arange(len(samples)), samples)).astype("<i2")
        offset_us = frame_offset * 1_000_000 // sample_rate
        word_offset = len(pronunciations)
        pronunciations.extend(
            replace(
                item, start_char=item.start_char + span.start, end_char=item.end_char + span.start
            )
            for item in turn.pronunciations
        )
        words.extend(
            replace(
                item,
                word_index=item.word_index + word_offset,
                start_us=item.start_us + offset_us,
                end_us=item.end_us + offset_us,
            )
            for item in turn.word_alignment or ()
        )
        phonemes.extend(
            replace(
                item,
                word_index=item.word_index + word_offset,
                start_us=item.start_us + offset_us,
                end_us=item.end_us + offset_us,
            )
            for item in turn.phoneme_alignment or ()
        )
        pcm_parts.append(pcm.tobytes())
        frame_offset += frames
    audio = pcm16_wav(b"".join(pcm_parts), sample_rate)
    return TeacherTurn(
        text=text,
        locale=locale,
        audio_wav=audio,
        sample_rate_hz=sample_rate,
        duration_us=inspect_wav(audio).duration_us,
        provider_id="local-speech-mixed-v1",
        pronunciations=tuple(pronunciations),
        word_alignment=tuple(words)
        if all(t.word_alignment is not None for _, t in parts)
        else None,
        phoneme_alignment=(
            tuple(phonemes) if all(t.phoneme_alignment is not None for _, t in parts) else None
        ),
        fallback_used=any(t.fallback_used for _, t in parts),
    )
