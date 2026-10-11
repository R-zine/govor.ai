"""Ephemeral-file adapter for the local whisper.cpp command-line recognizer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from govor_contracts import ProviderCapabilities
from govor_domain import DetectedLanguage, detect_language
from govor_provider_interfaces import (
    NoSpeechRecognized,
    ProviderMalformedOutput,
    ProviderResourceExhausted,
    ProviderUnavailable,
    Transcript,
    UtteranceAudio,
)


class WhisperCppRecognizer:
    capabilities = ProviderCapabilities(
        provider_id="whisper.cpp-small-multilingual",
        provider_kind="speech_recognition",
        local=True,
        features=frozenset({"english", "bulgarian", "language_detection", "offline"}),
    )

    def __init__(
        self,
        executable: str | Path,
        model: str | Path,
        *,
        timeout_seconds: float = 30.0,
        temporary_directory: str | Path = ".cache/local-ai-runtime",
    ) -> None:
        self._executable = Path(executable).resolve()
        self._model = Path(model).resolve()
        self._timeout = timeout_seconds
        self._temporary_directory = Path(temporary_directory).resolve()

    async def transcribe(self, audio: UtteranceAudio) -> Transcript:
        if audio.wav_bytes is None:
            raise ProviderUnavailable("whisper.cpp requires captured WAV audio")
        if not self._executable.is_file() or not self._model.is_file():
            raise ProviderUnavailable("whisper.cpp executable or model is missing")
        self._temporary_directory.mkdir(parents=True, exist_ok=True)
        wav_path: Path | None = None
        output_path: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=self._temporary_directory,
                prefix="utterance-",
                suffix=".wav",
                delete=False,
            ) as wav_file:
                wav_file.write(audio.wav_bytes)
                wav_path = Path(wav_file.name)
            output_base = wav_path.with_suffix("")
            output_path = Path(f"{output_base}.json")
            process = await asyncio.create_subprocess_exec(
                str(self._executable),
                "-m",
                str(self._model),
                "-f",
                str(wav_path),
                "-l",
                "auto",
                "-oj",
                "-of",
                str(output_base),
                "-np",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout,
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                raise
            if len(stdout) + len(stderr) > 1_048_576:
                raise ProviderMalformedOutput("whisper.cpp emitted excessive output")
            if process.returncode != 0:
                if process.returncode in {-9, 137}:
                    raise ProviderResourceExhausted("whisper.cpp was terminated by the system")
                raise ProviderUnavailable("whisper.cpp recognition failed")
            if not output_path.is_file() or output_path.stat().st_size > 1_048_576:
                raise ProviderMalformedOutput("whisper.cpp did not produce bounded JSON")
            return _parse_transcript(output_path.read_text(encoding="utf-8"))
        finally:
            for path in (wav_path, output_path):
                if path is not None:
                    path.unlink(missing_ok=True)


def _parse_transcript(raw: str) -> Transcript:
    try:
        data = json.loads(raw)
        segments = data["transcription"]
        if not isinstance(segments, list) or len(segments) > 1_000:
            raise ValueError("invalid transcription segment list")
        segment_texts: list[str] = []
        for segment in segments:
            if not isinstance(segment, dict) or not isinstance(segment.get("text"), str):
                raise ValueError("invalid transcription segment")
            segment_texts.append(segment["text"])
        text = "".join(segment_texts).strip()
        if len(text) > 2_048:
            raise ValueError("transcript is too long")
        reported_language = _reported_language(data)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ProviderMalformedOutput("whisper.cpp returned invalid JSON") from error
    if not text:
        raise NoSpeechRecognized("whisper.cpp found no usable speech")
    script_language = detect_language(text)
    language = script_language
    if script_language is DetectedLanguage.UNKNOWN and reported_language in {"en", "bg"}:
        language = DetectedLanguage(reported_language)
    locale = "bg-BG" if language is DetectedLanguage.BULGARIAN else "en-GB"
    return Transcript(
        text=text,
        locale=locale,
        language=language,
        provider_id="whisper.cpp-small-multilingual",
    )


def _reported_language(data: dict[str, object]) -> str | None:
    for container_name in ("result", "params"):
        container = data.get(container_name)
        if isinstance(container, dict):
            language = container.get("language")
            if isinstance(language, str):
                return language.removeprefix("auto:").split()[0]
    return None
