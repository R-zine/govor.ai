from pathlib import Path

import pytest
from govor_launcher.cli import ReleasePaths, _renderer_command


def test_release_renderer_is_silent_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOVOR_RENDERER_FIXTURE_TONE_DELAY_SECONDS", raising=False)
    command = _renderer_command(
        ReleasePaths.from_roots(tmp_path, tmp_path / "data"),
        tmp_path / "ca.pem",
    )

    assert "--no-startup-tone" in command
    assert not any(value.startswith("--startup-tone-delay-seconds=") for value in command)


def test_vm_fixture_can_schedule_the_bounded_muted_tone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOVOR_RENDERER_FIXTURE_TONE_DELAY_SECONDS", "60")
    command = _renderer_command(
        ReleasePaths.from_roots(tmp_path, tmp_path / "data"),
        tmp_path / "ca.pem",
    )

    assert "--mute-local-audio" in command
    assert "--no-startup-tone" not in command
    assert "--startup-tone-delay-seconds=60" in command


@pytest.mark.parametrize("value", ["later", "-1", "301"])
def test_vm_fixture_rejects_an_invalid_tone_delay(
    value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOVOR_RENDERER_FIXTURE_TONE_DELAY_SECONDS", value)

    with pytest.raises(RuntimeError, match="fixture tone delay"):
        _renderer_command(
            ReleasePaths.from_roots(tmp_path, tmp_path / "data"),
            tmp_path / "ca.pem",
        )
