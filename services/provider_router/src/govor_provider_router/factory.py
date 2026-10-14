"""Independent provider selection and lesson-pipeline composition."""

from __future__ import annotations

from typing import Literal, Protocol

from govor_local_ai.llama_cpp import LlamaCppDialogueProvider
from govor_local_ai.service import LocalLessonService
from govor_local_ai.whisper_cpp import WhisperCppRecognizer
from govor_progress import SQLiteProgressRepository
from govor_speech import build_local_speech_provider

from .adapters import (
    CloudAccessPolicy,
    OpenAiCompatibleDialogueProvider,
    OpenAiCompatibleSpeechProvider,
    OpenAiCompatibleSpeechRecognizer,
)
from .secrets import CredentialStore
from .windows_credentials import WindowsCredentialStore


class ProviderSettings(Protocol):
    recognition_provider: Literal["local", "cloud"]
    dialogue_provider: Literal["local", "cloud"]
    speech_provider: Literal["local", "cloud"]
    offline_only: bool
    llama_base_url: str
    whisper_executable: str
    whisper_model: str
    provider_timeout_seconds: float
    conversation_memory_turns: int
    dialogue_provider_id: str
    kokoro_model: str
    kokoro_voices: str
    kokoro_voice_gb: str
    kokoro_voice_us: str
    piper_bg_model: str
    piper_bg_config: str
    progress_database: str
    cloud_dialogue_base_url: str
    cloud_dialogue_model: str
    cloud_dialogue_credential_target: str
    cloud_recognition_base_url: str
    cloud_recognition_model: str
    cloud_recognition_credential_target: str
    cloud_speech_base_url: str
    cloud_speech_model: str
    cloud_speech_voice: str
    cloud_speech_credential_target: str


def build_configured_lesson_service(
    settings: ProviderSettings,
    *,
    credentials: CredentialStore | None = None,
) -> LocalLessonService:
    """Build one pipeline without coupling the three provider choices."""

    policy = CloudAccessPolicy(offline_only=settings.offline_only)
    needs_cloud = "cloud" in {
        settings.recognition_provider,
        settings.dialogue_provider,
        settings.speech_provider,
    }
    secret_store = credentials or (WindowsCredentialStore() if needs_cloud else None)

    recognizer = (
        WhisperCppRecognizer(
            settings.whisper_executable,
            settings.whisper_model,
            timeout_seconds=settings.provider_timeout_seconds,
        )
        if settings.recognition_provider == "local"
        else OpenAiCompatibleSpeechRecognizer(
            settings.cloud_recognition_base_url,
            settings.cloud_recognition_model,
            settings.cloud_recognition_credential_target,
            _required_store(secret_store),
            policy,
            timeout_seconds=settings.provider_timeout_seconds,
            transport=None,
        )
    )
    dialogue = (
        LlamaCppDialogueProvider(
            settings.llama_base_url,
            timeout_seconds=max(1.0, settings.provider_timeout_seconds / 2),
            provider_id=settings.dialogue_provider_id,
        )
        if settings.dialogue_provider == "local"
        else OpenAiCompatibleDialogueProvider(
            settings.cloud_dialogue_base_url,
            settings.cloud_dialogue_model,
            settings.cloud_dialogue_credential_target,
            _required_store(secret_store),
            policy,
            timeout_seconds=settings.provider_timeout_seconds,
            transport=None,
        )
    )
    speech = (
        build_local_speech_provider(settings)
        if settings.speech_provider == "local"
        else OpenAiCompatibleSpeechProvider(
            settings.cloud_speech_base_url,
            settings.cloud_speech_model,
            settings.cloud_speech_voice,
            settings.cloud_speech_credential_target,
            _required_store(secret_store),
            policy,
            timeout_seconds=settings.provider_timeout_seconds,
            transport=None,
        )
    )
    return LocalLessonService(
        recognizer=recognizer,
        dialogue=dialogue,
        speech=speech,
        progress_repository=SQLiteProgressRepository(settings.progress_database),
        memory_turns=settings.conversation_memory_turns,
    )


def _required_store(store: CredentialStore | None) -> CredentialStore:
    if store is None:
        raise RuntimeError("cloud provider composition requires a credential store")
    return store
