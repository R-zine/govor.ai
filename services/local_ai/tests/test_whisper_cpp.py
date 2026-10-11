from __future__ import annotations

import json
from uuid import uuid4

import pytest
from govor_domain import DetectedLanguage
from govor_local_ai.whisper_cpp import WhisperCppRecognizer, _parse_transcript
from govor_provider_interfaces import (
    NoSpeechRecognized,
    ProviderMalformedOutput,
    ProviderUnavailable,
    UtteranceAudio,
)


def test_parses_english_bulgarian_and_mixed_transcripts() -> None:
    english = _parse_transcript(
        '{"result":{"language":"en"},"transcription":[{"text":" Coffee, please."}]}'
    )
    bulgarian = _parse_transcript(
        '{"result":{"language":"bg"},"transcription":[{"text":" Кафе, моля."}]}'
    )
    mixed = _parse_transcript(
        '{"result":{"language":"bg"},"transcription":[{"text":" Кафе please."}]}'
    )

    assert english.language is DetectedLanguage.ENGLISH
    assert bulgarian.language is DetectedLanguage.BULGARIAN
    assert mixed.language is DetectedLanguage.MIXED


def test_distinguishes_no_speech_from_malformed_recognizer_output() -> None:
    with pytest.raises(ProviderMalformedOutput):
        _parse_transcript("{}")
    with pytest.raises(ProviderMalformedOutput):
        _parse_transcript('{"transcription":[{"text":42}]}')
    with pytest.raises(NoSpeechRecognized):
        _parse_transcript('{"transcription":[]}')


@pytest.mark.asyncio
async def test_missing_runtime_fails_without_persisting_audio(tmp_path) -> None:
    recognizer = WhisperCppRecognizer(
        tmp_path / "missing-whisper.exe",
        tmp_path / "missing-model.bin",
        temporary_directory=tmp_path / "runtime",
    )
    audio = UtteranceAudio(
        uuid4(),
        500_000,
        b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 32,
    )

    with pytest.raises(ProviderUnavailable):
        await recognizer.transcribe(audio)
    assert not (tmp_path / "runtime").exists()


@pytest.mark.asyncio
async def test_recognizer_runs_process_and_removes_ephemeral_files(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "whisper-cli.exe"
    model = tmp_path / "model.bin"
    executable.touch()
    model.touch()

    class Process:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def create_process(*arguments, **kwargs):  # type: ignore[no-untyped-def]
        _ = kwargs
        output_base = arguments[arguments.index("-of") + 1]
        output = {
            "result": {"language": "en"},
            "transcription": [{"text": " Coffee, please."}],
        }
        (tmp_path / "runtime" / f"{(tmp_path / output_base).name}.json").write_text(
            json.dumps(output), encoding="utf-8"
        )
        return Process()

    monkeypatch.setattr("govor_local_ai.whisper_cpp.asyncio.create_subprocess_exec", create_process)
    runtime = tmp_path / "runtime"
    recognizer = WhisperCppRecognizer(executable, model, temporary_directory=runtime)
    audio = UtteranceAudio(
        uuid4(),
        500_000,
        b"RIFF" + b"\0" * 4 + b"WAVE" + b"\0" * 32,
    )

    result = await recognizer.transcribe(audio)

    assert result.text == "Coffee, please."
    assert list(runtime.iterdir()) == []
