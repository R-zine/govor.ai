from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOVOR_", extra="ignore")

    mode: Literal["fake", "local"] = "fake"
    bind_host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1024, le=65535)
    max_control_message_bytes: int = Field(default=1_048_576, ge=1024, le=4_194_304)
    provider_timeout_seconds: float = Field(default=30.0, gt=0.0, le=60.0)
    capture_timeout_seconds: float = Field(default=2.0, gt=0.0, le=10.0)
    renderer_ack_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    playback_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    recording_timeout_seconds: float = Field(default=60.0, gt=0.0, le=120.0)
    renderer_required: bool = True
    media_capture_url: str = "http://127.0.0.1:8766"
    llama_base_url: str = "http://127.0.0.1:8767"
    dialogue_provider_id: str = Field(
        default="llama.cpp-qwen3-4b-q4_k_m",
        min_length=1,
        max_length=64,
    )
    whisper_executable: str = ".tools/whisper.cpp/b5454/Release/whisper-cli.exe"
    whisper_model: str = ".tools/models/whisper/ggml-small.bin"
    conversation_memory_turns: int = Field(default=8, ge=1, le=32)
    kokoro_model: str = ".tools/models/speech/kokoro-v1.0.onnx"
    kokoro_voices: str = ".tools/models/speech/voices-v1.0.bin"
    kokoro_voice_gb: str = "bf_emma"
    kokoro_voice_us: str = "af_heart"
    piper_bg_model: str = ".tools/models/speech/bg_BG-dimitar-medium.onnx"
    piper_bg_config: str = ".tools/models/speech/bg_BG-dimitar-medium.onnx.json"
    progress_database: str = "data/progress.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
