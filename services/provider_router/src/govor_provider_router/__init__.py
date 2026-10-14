"""Provider selection, opt-in cloud adapters, and protected credentials."""

from .adapters import (
    CloudAccessPolicy,
    OpenAiCompatibleDialogueProvider,
    OpenAiCompatibleSpeechProvider,
    OpenAiCompatibleSpeechRecognizer,
)
from .secrets import CredentialStore, InMemoryCredentialStore
from .windows_credentials import WindowsCredentialStore

__all__ = [
    "CloudAccessPolicy",
    "CredentialStore",
    "InMemoryCredentialStore",
    "OpenAiCompatibleDialogueProvider",
    "OpenAiCompatibleSpeechProvider",
    "OpenAiCompatibleSpeechRecognizer",
    "WindowsCredentialStore",
]
