from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOVOR_", extra="ignore")

    mode: Literal["fake", "production"] = "fake"
    bind_host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1024, le=65535)
    max_control_message_bytes: int = Field(default=1_048_576, ge=1024, le=4_194_304)
    provider_timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)
    renderer_ack_timeout_seconds: float = Field(default=2.0, gt=0.0, le=30.0)
    playback_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    recording_timeout_seconds: float = Field(default=30.0, gt=0.0, le=120.0)
    renderer_required: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
