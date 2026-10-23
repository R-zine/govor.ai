from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOVOR_", extra="ignore")

    mode: Literal["fake", "local"] = "fake"
    offline_only: bool = True
    recognition_provider: Literal["local", "cloud"] = "local"
    dialogue_provider: Literal["local", "cloud"] = "local"
    speech_provider: Literal["local", "cloud"] = "local"
    allow_cloud_microphone_upload: bool = False
    bind_host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1024, le=65535)
    secure_gateway: bool = False
    gateway_credentials_file: str | None = None
    max_control_message_bytes: int = Field(default=1_048_576, ge=1024, le=4_194_304)
    provider_timeout_seconds: float = Field(default=30.0, gt=0.0, le=60.0)
    capture_timeout_seconds: float = Field(default=2.0, gt=0.0, le=10.0)
    renderer_ack_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    playback_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    recording_timeout_seconds: float = Field(default=60.0, gt=0.0, le=120.0)
    renderer_required: bool = True
    media_capture_url: str = "http://127.0.0.1:8766"
    media_capture_tls_ca: str | None = None
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
    lesson_directory: str = "assets/lesson-content"
    cloud_dialogue_base_url: str = "https://api.openai.com/v1"
    cloud_dialogue_model: str = "gpt-4.1-mini"
    cloud_dialogue_credential_target: str = Field(
        default="openai-dialogue", pattern=r"^[a-z][a-z0-9._-]{1,63}$"
    )
    cloud_recognition_base_url: str = "https://api.openai.com/v1"
    cloud_recognition_model: str = "gpt-4o-mini-transcribe"
    cloud_recognition_credential_target: str = Field(
        default="openai-recognition", pattern=r"^[a-z][a-z0-9._-]{1,63}$"
    )
    cloud_speech_base_url: str = "https://api.openai.com/v1"
    cloud_speech_model: str = "gpt-4o-mini-tts"
    cloud_speech_voice: str = "coral"
    cloud_speech_credential_target: str = Field(
        default="openai-speech", pattern=r"^[a-z][a-z0-9._-]{1,63}$"
    )

    @model_validator(mode="after")
    def validate_cloud_opt_in(self) -> Settings:
        if self.bind_host not in {"127.0.0.1", "::1"} and (
            not self.secure_gateway or not self.gateway_credentials_file
        ):
            raise ValueError(
                "a LAN control bind requires the secure gateway and a credential store"
            )
        if self.secure_gateway and not self.gateway_credentials_file:
            raise ValueError("the secure gateway requires a credential store")
        selected = {
            self.recognition_provider,
            self.dialogue_provider,
            self.speech_provider,
        }
        if "cloud" in selected and self.offline_only:
            raise ValueError("cloud providers require offline_only=false")
        if self.recognition_provider == "cloud" and not self.allow_cloud_microphone_upload:
            raise ValueError("cloud recognition requires explicit microphone-upload consent")
        endpoints = []
        if self.dialogue_provider == "cloud":
            endpoints.append(self.cloud_dialogue_base_url)
        if self.recognition_provider == "cloud":
            endpoints.append(self.cloud_recognition_base_url)
        if self.speech_provider == "cloud":
            endpoints.append(self.cloud_speech_base_url)
        for endpoint in endpoints:
            parsed = urlparse(endpoint)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("cloud provider endpoints must be credential-free HTTPS URLs")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
