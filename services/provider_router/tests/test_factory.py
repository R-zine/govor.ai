from __future__ import annotations

from govor_host.config import Settings
from govor_provider_router import InMemoryCredentialStore
from govor_provider_router.factory import build_configured_lesson_service


def test_all_three_provider_subsystems_can_be_selected_independently(tmp_path) -> None:  # type: ignore[no-untyped-def]
    cloud = build_configured_lesson_service(
        Settings(
            mode="local",
            offline_only=False,
            recognition_provider="cloud",
            dialogue_provider="cloud",
            speech_provider="cloud",
            allow_cloud_microphone_upload=True,
            progress_database=str(tmp_path / "cloud.sqlite3"),
        ),
        credentials=InMemoryCredentialStore(),
    )
    mixed = build_configured_lesson_service(
        Settings(
            mode="local",
            offline_only=False,
            recognition_provider="local",
            dialogue_provider="cloud",
            speech_provider="local",
            progress_database=str(tmp_path / "mixed.sqlite3"),
        ),
        credentials=InMemoryCredentialStore(),
    )

    assert [item.local for item in cloud.capabilities] == [False, False, False]
    assert [item.local for item in mixed.capabilities] == [True, False, True]
    assert [item.provider_kind for item in mixed.capabilities] == [
        "speech_recognition",
        "dialogue",
        "speech_synthesis",
    ]
