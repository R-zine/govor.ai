"""Accent-aware IPA and conservative timing conversion."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass

from govor_provider_interfaces import PhonemeAlignment, Pronunciation, WordAlignment

_WORD_PATTERN = re.compile(r"[^\W_]+(?:['\N{RIGHT SINGLE QUOTATION MARK}-][^\W_]+)*", re.UNICODE)
_PHONEMIZER_LOCK = threading.Lock()
_BOUNDARIES = frozenset({"^", "$"})
_NON_SPEECH = frozenset({"^", "$", "_", ".", ",", "!", "?", ":", ";", "-"})


@dataclass(frozen=True, slots=True)
class RawPhonemeTiming:
    symbol: str
    start_us: int
    end_us: int


def pronunciations_for(text: str, locale: str) -> tuple[Pronunciation, ...]:
    words = tuple(_WORD_PATTERN.finditer(text))
    if not words:
        return ()
    language = _espeak_locale(locale)
    values = _phonemize([match.group(0) for match in words], language)
    if len(values) != len(words):
        raise ValueError("phonemizer did not return one pronunciation per word")
    return tuple(
        Pronunciation(
            word=match.group(0),
            start_char=match.start(),
            end_char=match.end(),
            ipa=ipa,
            locale=locale,
            explanation=_explain(ipa, locale),
        )
        for match, ipa in zip(words, values, strict=True)
    )


def align_to_words(
    timings: tuple[RawPhonemeTiming, ...],
    word_count: int,
) -> tuple[tuple[WordAlignment, ...] | None, tuple[PhonemeAlignment, ...] | None]:
    """Map provider-reported phoneme spans to words, or return explicit absence.

    The mapping is accepted only when whitespace/sentence boundaries produce exactly the same
    number of groups as the independently tokenized source text. No proportional timing is
    synthesized when that invariant fails.
    """

    if not timings or word_count <= 0:
        return None, None
    groups: list[list[RawPhonemeTiming]] = []
    current: list[RawPhonemeTiming] = []
    for timing in timings:
        symbol = timing.symbol
        if symbol.isspace() or symbol in _BOUNDARIES:
            if current:
                groups.append(current)
                current = []
            continue
        current.append(timing)
    if current:
        groups.append(current)
    if len(groups) != word_count:
        return None, None

    words: list[WordAlignment] = []
    phonemes: list[PhonemeAlignment] = []
    for word_index, group in enumerate(groups):
        spoken = [item for item in group if item.symbol not in _NON_SPEECH]
        if not spoken:
            return None, None
        words.append(
            WordAlignment(
                word_index=word_index,
                start_us=spoken[0].start_us,
                end_us=spoken[-1].end_us,
            )
        )
        phonemes.extend(
            PhonemeAlignment(
                word_index=word_index,
                symbol=item.symbol,
                start_us=item.start_us,
                end_us=item.end_us,
            )
            for item in spoken
        )
    return tuple(words), tuple(phonemes)


def _phonemize(words: list[str], language: str) -> list[str]:
    import espeakng_loader  # type: ignore[import-untyped]
    from phonemizer import phonemize  # type: ignore[import-untyped]
    from phonemizer.backend.espeak.wrapper import (  # type: ignore[import-untyped]
        EspeakWrapper,
    )
    from phonemizer.separator import Separator  # type: ignore[import-untyped]

    with _PHONEMIZER_LOCK:
        EspeakWrapper.set_library(espeakng_loader.get_library_path())
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
        result = phonemize(
            words,
            language=language,
            backend="espeak",
            separator=Separator(phone="", word=" ", syllable=""),
            strip=True,
            preserve_punctuation=False,
            with_stress=True,
            language_switch="remove-flags",
            njobs=1,
        )
    values = [result] if isinstance(result, str) else list(result)
    cleaned = [re.sub(r"\([^)]*\)", "", value).strip() for value in values]
    if any(not value for value in cleaned):
        raise ValueError("phonemizer returned an empty pronunciation")
    return cleaned


def _espeak_locale(locale: str) -> str:
    return {
        "en-GB": "en-gb",
        "en-US": "en-us",
        "bg-BG": "bg",
    }.get(locale) or _unsupported_locale(locale)


def _unsupported_locale(locale: str) -> str:
    raise ValueError(f"unsupported speech locale: {locale}")


def _explain(ipa: str, locale: str) -> str | None:
    if not locale.startswith("en-"):
        return None
    notes = (
        ("θ", "За /θ/ сложете върха на езика леко между зъбите и издишайте без глас."),
        ("ð", "За /ð/ поставете езика като при /θ/, но включете гласа."),
        ("æ", "За /æ/ отворете устата широко; звукът е между българските „а“ и „е“."),
        ("ə", "/ə/ е кратък, неударен неутрален звук; отпуснете устата."),
        ("ɜ", "За /ɜː/ дръжте езика централно и удължете ударената гласна."),
        ("ɹ", "Английското /ɹ/ се произнася без трептене на върха на езика."),
        ("w", "За /w/ закръглете устните, после бързо преминете към гласната."),
    )
    selected = [note for symbol, note in notes if symbol in ipa]
    stress = " Знакът /ˈ/ показва ударената сричка." if "ˈ" in ipa else ""
    if selected:
        return " ".join(selected[:2]) + stress
    return stress.strip() or None
