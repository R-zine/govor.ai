from __future__ import annotations

import pytest
from govor_host.config import Settings
from pydantic import ValidationError


def test_default_configuration_is_fully_local_and_offline() -> None:
    settings = Settings()

    assert settings.offline_only
    assert settings.recognition_provider == "local"
    assert settings.dialogue_provider == "local"
    assert settings.speech_provider == "local"
    assert not settings.allow_cloud_microphone_upload


@pytest.mark.parametrize("field", ["recognition_provider", "dialogue_provider", "speech_provider"])
def test_each_cloud_provider_requires_offline_mode_to_be_disabled(field: str) -> None:
    with pytest.raises(ValidationError, match="offline_only=false"):
        Settings(**{field: "cloud"})


def test_cloud_microphone_upload_requires_separate_explicit_consent() -> None:
    with pytest.raises(ValidationError, match="microphone-upload consent"):
        Settings(offline_only=False, recognition_provider="cloud")

    settings = Settings(
        offline_only=False,
        recognition_provider="cloud",
        allow_cloud_microphone_upload=True,
    )
    assert settings.dialogue_provider == "local"
    assert settings.speech_provider == "local"


def test_cloud_endpoint_must_be_credential_free_https() -> None:
    with pytest.raises(ValidationError, match="credential-free HTTPS"):
        Settings(
            offline_only=False,
            dialogue_provider="cloud",
            cloud_dialogue_base_url="http://key@provider.example/v1?unsafe=true",
        )
