"""Process-isolated eSpeak NG WAV synthesis used by the offline fallback."""

from __future__ import annotations

import argparse
import ctypes
import io
import sys
import wave
from typing import Any

import espeakng_loader  # type: ignore[import-untyped]

_AUDIO_OUTPUT_RETRIEVAL = 1
_EE_OK = 0
_PARAMETER_RATE = 1
_CHARS_UTF8 = 1
_END_PAUSE = 0x1000


def synthesize(text: str, voice: str, rate: int) -> bytes:
    library = ctypes.CDLL(espeakng_loader.get_library_path())
    callback_type = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_short),
        ctypes.c_int,
        ctypes.c_void_p,
    )
    chunks: list[bytes] = []

    def receive(samples: Any, count: int, _events: Any) -> int:
        if samples and count > 0:
            chunks.append(ctypes.string_at(samples, count * ctypes.sizeof(ctypes.c_short)))
        return 0

    callback = callback_type(receive)

    library.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    library.espeak_Initialize.restype = ctypes.c_int
    library.espeak_SetSynthCallback.argtypes = [callback_type]
    library.espeak_SetSynthCallback.restype = None
    library.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
    library.espeak_SetVoiceByName.restype = ctypes.c_int
    library.espeak_SetParameter.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    library.espeak_SetParameter.restype = ctypes.c_int
    library.espeak_Synth.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.c_void_p,
    ]
    library.espeak_Synth.restype = ctypes.c_int
    library.espeak_Synchronize.argtypes = []
    library.espeak_Synchronize.restype = ctypes.c_int
    library.espeak_Terminate.argtypes = []
    library.espeak_Terminate.restype = ctypes.c_int

    sample_rate = library.espeak_Initialize(
        _AUDIO_OUTPUT_RETRIEVAL,
        100,
        espeakng_loader.get_data_path().encode("utf-8"),
        0,
    )
    if sample_rate <= 0:
        raise RuntimeError("eSpeak NG initialization failed")
    library.espeak_SetSynthCallback(callback)
    if library.espeak_SetVoiceByName(voice.encode("ascii")) != _EE_OK:
        raise RuntimeError("eSpeak NG voice is unavailable")
    if library.espeak_SetParameter(_PARAMETER_RATE, rate, 0) != _EE_OK:
        raise RuntimeError("eSpeak NG rate could not be set")
    encoded = text.encode("utf-8") + b"\0"
    identifier = ctypes.c_uint(0)
    result = library.espeak_Synth(
        encoded,
        len(encoded),
        0,
        0,
        0,
        _CHARS_UTF8 | _END_PAUSE,
        ctypes.byref(identifier),
        None,
    )
    if result != _EE_OK or library.espeak_Synchronize() != _EE_OK:
        raise RuntimeError("eSpeak NG synthesis failed")
    library.espeak_Terminate()
    pcm = b"".join(chunks)
    if not pcm:
        raise RuntimeError("eSpeak NG returned empty audio")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--voice",
        required=True,
        choices=("en", "en-us", "bg", "en+f3", "en-us+f3", "bg+f3"),
    )
    parser.add_argument("--rate", required=True, type=int)
    args = parser.parse_args()
    text = sys.stdin.buffer.read(8_193).decode("utf-8")
    if not 1 <= len(text) <= 2_048 or not 80 <= args.rate <= 450:
        raise ValueError("fallback synthesis input is outside accepted bounds")
    sys.stdout.buffer.write(synthesize(text, args.voice, args.rate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
