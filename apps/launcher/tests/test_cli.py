import json
import shutil
from pathlib import Path

import pytest
from govor_launcher.cli import (
    ReleasePaths,
    _doctor,
    _release_environment,
    _renderer_command,
    main,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_release_doctor_requires_packaged_lesson_content(tmp_path: Path) -> None:
    paths = ReleasePaths.from_roots(tmp_path, tmp_path / "data")
    for required in (paths.python, paths.llama, paths.whisper, paths.renderer, paths.manifest):
        _touch(required)

    with pytest.raises(RuntimeError, match="no guided lesson definitions"):
        _doctor(paths, require_models=False)


def test_release_environment_selects_packaged_lesson_directory(tmp_path: Path) -> None:
    paths = ReleasePaths.from_roots(tmp_path, tmp_path / "data")

    environment = _release_environment(paths, tmp_path / "ca.pem")

    assert environment["GOVOR_LESSON_DIRECTORY"] == str(tmp_path / "content" / "lessons")


def test_import_lessons_command_installs_into_the_packaged_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_root = tmp_path / "install"
    shutil.copytree(
        REPOSITORY_ROOT / "assets" / "lesson-content",
        install_root / "content" / "lessons",
    )
    source = tmp_path / "hotel.json"
    lesson = json.loads(
        (REPOSITORY_ROOT / "assets" / "lesson-content" / "cafe-ordering.json").read_text(
            encoding="utf-8"
        )
    )
    lesson.update({"scenario_id": "hotel-check-in", "title": "Hotel", "display_order": 50})
    source.write_text(json.dumps(lesson), encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))

    result = main(
        [
            "--install-root",
            str(install_root),
            "import-lessons",
            "--source",
            str(source),
        ]
    )

    assert result == 0
    assert (install_root / "content" / "lessons" / "hotel-check-in.json").is_file()
    assert "Imported: Hotel (hotel-check-in)" in capsys.readouterr().out


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
