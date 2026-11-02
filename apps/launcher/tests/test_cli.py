import json
import os
import shutil
import zipfile
from pathlib import Path

import govor_launcher.cli as launcher_cli
import pytest
from govor_launcher.cli import (
    ReleasePaths,
    _doctor,
    _launch_application_patch,
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
    assert environment["GOVOR_ENVIRONMENT_DIRECTORY"] == str(tmp_path / "content" / "environments")


def test_start_command_forwards_an_explicit_lan_address(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    def fake_start(
        paths: ReleasePaths,
        *,
        smoke_seconds: float | None,
        lan_address: str | None,
    ) -> int:
        received.update(
            paths=paths,
            smoke_seconds=smoke_seconds,
            lan_address=lan_address,
        )
        return 0

    monkeypatch.setattr(launcher_cli, "_start", fake_start)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))

    result = main(
        [
            "--install-root",
            str(tmp_path / "install"),
            "start",
            "--smoke-seconds",
            "5",
            "--lan-address",
            "192.168.1.20",
        ]
    )

    assert result == 0
    assert received["smoke_seconds"] == 5.0
    assert received["lan_address"] == "192.168.1.20"


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
    (install_root / "content" / "environments").mkdir(parents=True)
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


def test_create_lesson_command_rejects_an_out_of_bounds_length_before_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_root = tmp_path / "install"
    shutil.copytree(
        REPOSITORY_ROOT / "assets" / "lesson-content",
        install_root / "content" / "lessons",
    )
    (install_root / "content" / "environments").mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))

    result = main(
        [
            "--install-root",
            str(install_root),
            "create-lesson",
            "--topic",
            "Hotel check-in",
            "--exercise-count",
            "9",
        ]
    )

    assert result == 2
    assert "between one and eight" in capsys.readouterr().err
    assert len(tuple((install_root / "content" / "lessons").glob("*.json"))) == 4


def test_import_and_list_environments_use_the_packaged_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_root = tmp_path / "install"
    environments = install_root / "content" / "environments"
    environments.mkdir(parents=True)
    source = tmp_path / "hotel.zip"
    fixture = REPOSITORY_ROOT / "tests/fixtures/contracts/valid/environment-hotel-lobby.json"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("hotel.json", fixture.read_bytes())
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "data"))

    assert (
        main(["--install-root", str(install_root), "import-environments", "--source", str(source)])
        == 0
    )
    assert (environments / "hotel-lobby.json").is_file()
    capsys.readouterr()

    assert main(["--install-root", str(install_root), "list-environments", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result[-1] == {"environment_id": "hotel-lobby", "display_name": "Hotel lobby"}


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


def test_release_renderer_receives_only_the_temporary_qr_path(
    tmp_path: Path,
) -> None:
    paths = ReleasePaths.from_roots(tmp_path, tmp_path / "data")

    command = _renderer_command(
        paths,
        tmp_path / "ca.pem",
        paths.pairing_qr,
        paths.pairing_bootstrap,
    )

    assert f"--pairing-qr={paths.pairing_qr}" in command
    assert f"--pairing-bootstrap={paths.pairing_bootstrap}" in command
    assert not any("12345678" in value or "certificate_sha256" in value for value in command)


def test_application_patch_ui_launches_only_the_installed_command_after_shutdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = ReleasePaths.from_roots(tmp_path, tmp_path / "data")
    _touch(tmp_path / "Apply-Govor-Patch.cmd")
    launched: dict[str, object] = {}

    def fake_popen(command: list[str], **kwargs: object) -> object:
        launched.update(command=command, **kwargs)
        return object()

    monkeypatch.setattr("govor_launcher.cli.subprocess.Popen", fake_popen)

    _launch_application_patch(paths)

    assert launched["command"] == [
        str(Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32" / "cmd.exe"),
        "/d",
        "/c",
        str(tmp_path / "Apply-Govor-Patch.cmd"),
    ]
    assert launched["cwd"] == tmp_path


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
