"""Create bounded mouth-animation data from actual synthesized PCM and provider timing."""

from __future__ import annotations

import math
import sys
import wave
from array import array
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

Viseme = Literal["silence", "closed", "open", "wide", "round", "teeth"]


@dataclass(frozen=True, slots=True)
class TimedPhoneme:
    symbol: str
    start_us: int
    end_us: int

    def __post_init__(self) -> None:
        if not self.symbol or self.start_us < 0 or self.end_us <= self.start_us:
            raise ValueError("timed phoneme is invalid")


@dataclass(frozen=True, slots=True)
class SpeechEnergySample:
    media_time_us: int
    level_milli: int


@dataclass(frozen=True, slots=True)
class VisemeCue:
    viseme: Viseme
    start_us: int
    end_us: int


@dataclass(frozen=True, slots=True)
class AvatarAnimation:
    duration_us: int
    gesture: Literal["speaking"]
    expression: Literal["encouraging"]
    viseme_source: Literal["provider_phoneme_alignment", "none"]
    speech_energy: tuple[SpeechEnergySample, ...]
    visemes: tuple[VisemeCue, ...]


def build_avatar_animation(
    audio_wav: bytes,
    duration_us: int,
    phonemes: Iterable[TimedPhoneme] | None,
) -> AvatarAnimation:
    """Build an animation without estimating phoneme timing.

    Energy offsets come directly from PCM sample positions. Viseme offsets are emitted only when
    the speech provider supplied phoneme alignment; otherwise the energy envelope drives a generic
    mouth opening and ``viseme_source`` remains explicit ``none``.
    """

    if not 1 <= duration_us <= 30_000_000:
        raise ValueError("avatar duration is outside the accepted range")
    energy = _speech_energy(audio_wav, duration_us)
    timed_phonemes = tuple(phonemes or ())
    for phoneme in timed_phonemes:
        if phoneme.end_us > duration_us:
            raise ValueError("phoneme alignment exceeds avatar duration")
    visemes = _viseme_cues(timed_phonemes)
    return AvatarAnimation(
        duration_us=duration_us,
        gesture="speaking",
        expression="encouraging",
        viseme_source=("provider_phoneme_alignment" if timed_phonemes else "none"),
        speech_energy=energy,
        visemes=visemes,
    )


def _speech_energy(audio_wav: bytes, duration_us: int) -> tuple[SpeechEnergySample, ...]:
    try:
        with wave.open(BytesIO(audio_wav), "rb") as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
                raise ValueError("avatar audio must be mono PCM16 WAV")
            sample_rate = stream.getframerate()
            frames = stream.readframes(stream.getnframes())
    except (EOFError, wave.Error) as error:
        raise ValueError("avatar audio is not a valid WAV") from error

    samples = array("h")
    samples.frombytes(frames)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise ValueError("avatar audio contains no samples")

    window_frames = max(1, sample_rate // 25)  # 40 ms; at most 750 samples for 30 seconds.
    rms_values: list[tuple[int, float]] = []
    for start in range(0, len(samples), window_frames):
        window = samples[start : start + window_frames]
        square_sum = sum(int(sample) * int(sample) for sample in window)
        rms_values.append((start, math.sqrt(square_sum / len(window))))
    peak = max(value for _, value in rms_values)
    return tuple(
        SpeechEnergySample(
            media_time_us=min(duration_us, start * 1_000_000 // sample_rate),
            level_milli=(0 if peak == 0 else min(1_000, round(value * 1_000 / peak))),
        )
        for start, value in rms_values
    )


def _viseme_cues(phonemes: tuple[TimedPhoneme, ...]) -> tuple[VisemeCue, ...]:
    cues: list[VisemeCue] = []
    for phoneme in phonemes:
        cue = VisemeCue(_phoneme_to_viseme(phoneme.symbol), phoneme.start_us, phoneme.end_us)
        if cues and cues[-1].viseme == cue.viseme and cues[-1].end_us == cue.start_us:
            previous = cues[-1]
            cues[-1] = VisemeCue(previous.viseme, previous.start_us, cue.end_us)
        else:
            cues.append(cue)
    return tuple(cues)


def _phoneme_to_viseme(symbol: str) -> Viseme:
    normalized = symbol.casefold().replace("ˈ", "").replace("ˌ", "").strip()
    if not normalized or normalized in {"sil", "sp", "_"}:
        return "silence"
    if any(sound in normalized for sound in ("p", "b", "m")):
        return "closed"
    if any(sound in normalized for sound in ("f", "v")):
        return "teeth"
    if any(sound in normalized for sound in ("u", "o", "ɔ", "ʊ", "w")):
        return "round"
    if any(sound in normalized for sound in ("i", "e", "ɪ", "ɛ", "j")):
        return "wide"
    return "open"
