from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_windows_entrypoints_pass_a_normalized_install_root() -> None:
    for name in ("Setup-Govor.cmd", "Start-Govor.cmd"):
        script = (REPOSITORY_ROOT / "distribution" / "windows" / name).read_text(encoding="utf-8")

        assert 'for %%I in ("%~dp0.") do set "GOVOR_INSTALL_ROOT=%%~fI"' in script
        assert '--install-root "%GOVOR_INSTALL_ROOT%"' in script
        assert '--install-root "%~dp0"' not in script
        assert "--doctor-only" in script


def test_lesson_manager_uses_a_native_picker_and_local_import_command() -> None:
    command = (REPOSITORY_ROOT / "distribution" / "windows" / "Manage-Lessons.cmd").read_text(
        encoding="utf-8"
    )
    picker = (REPOSITORY_ROOT / "distribution" / "windows" / "Import-Lessons.ps1").read_text(
        encoding="utf-8"
    )
    packager = (REPOSITORY_ROOT / "scripts" / "package.ps1").read_text(encoding="utf-8")

    assert "Import-Lessons.ps1" in command
    assert "Windows.Forms.OpenFileDialog" in picker
    assert "*.json;*.zip" in picker
    assert "import-lessons --source $dialog.FileName" in picker
    assert "Invoke-WebRequest" not in picker
    assert "Manage-Lessons.cmd" in packager
    assert "Import-Lessons.ps1" in packager


def test_lesson_creator_uses_the_loopback_backend_and_is_packaged() -> None:
    command = (REPOSITORY_ROOT / "distribution" / "windows" / "Create-Lesson.cmd").read_text(
        encoding="utf-8"
    )
    creator = (REPOSITORY_ROOT / "distribution" / "windows" / "Create-Lesson.ps1").read_text(
        encoding="utf-8"
    )
    packager = (REPOSITORY_ROOT / "scripts" / "package.ps1").read_text(encoding="utf-8")

    assert "Create-Lesson.ps1" in command
    assert "Windows.Forms.Form" in creator
    assert "create-lesson" in creator
    assert "--topic" in creator
    assert "--difficulty" in creator
    assert "--environment" in creator
    assert "--exercise-count" in creator
    assert "Invoke-WebRequest" not in creator
    assert "Create-Lesson.cmd" in packager
    assert "Create-Lesson.ps1" in packager
    assert "list-environments --json" in creator


def test_environment_manager_uses_a_zip_picker_and_local_import_command() -> None:
    command = (REPOSITORY_ROOT / "distribution" / "windows" / "Manage-Environments.cmd").read_text(
        encoding="utf-8"
    )
    picker = (REPOSITORY_ROOT / "distribution" / "windows" / "Import-Environments.ps1").read_text(
        encoding="utf-8"
    )
    packager = (REPOSITORY_ROOT / "scripts" / "package.ps1").read_text(encoding="utf-8")

    assert "Import-Environments.ps1" in command
    assert "Windows.Forms.OpenFileDialog" in picker
    assert "*.zip" in picker
    assert "import-environments --source $dialog.FileName" in picker
    assert "Invoke-WebRequest" not in picker
    assert "Manage-Environments.cmd" in packager
    assert "Import-Environments.ps1" in packager


def test_application_patch_entrypoint_uses_the_installed_signed_updater() -> None:
    command = (REPOSITORY_ROOT / "distribution" / "windows" / "Apply-Govor-Patch.cmd").read_text(
        encoding="utf-8"
    )
    updater = (REPOSITORY_ROOT / "distribution" / "windows" / "Apply-Govor-Patch.ps1").read_text(
        encoding="utf-8"
    )
    packager = (REPOSITORY_ROOT / "scripts" / "package.ps1").read_text(encoding="utf-8")

    assert "Apply-Govor-Patch.ps1" in command
    assert "--doctor-only" in command
    assert "-DoctorOnly" in command
    assert "RSACryptoServiceProvider" in updater
    assert "VerifyData" in updater
    assert "old_sha256" in updater
    assert "Required base file was locally changed" in updater
    assert "File]::Replace" in updater
    assert "rolled back" in updater
    assert "Start-Process" not in updater
    assert "Invoke-WebRequest" not in updater
    assert "Apply-Govor-Patch.cmd" in packager
    assert "Apply-Govor-Patch.ps1" in packager
    assert "update-signing-public.xml" in packager
    assert "Apply-Govor-Patch.cmd'), '--doctor-only'" in packager


def test_start_entrypoint_forwards_bounded_smoke_arguments() -> None:
    script = (REPOSITORY_ROOT / "distribution" / "windows" / "Start-Govor.cmd").read_text(
        encoding="utf-8"
    )

    assert 'set "PYTHONUNBUFFERED=1"' in script
    assert '--install-root "%GOVOR_INSTALL_ROOT%" start %*' in script


def test_setup_installs_an_integrity_pinned_microsoft_cpp_runtime() -> None:
    setup = (REPOSITORY_ROOT / "distribution" / "windows" / "Setup-Govor.cmd").read_text(
        encoding="utf-8"
    )
    prerequisite = (
        REPOSITORY_ROOT / "distribution" / "windows" / "Install-Prerequisites.ps1"
    ).read_text(encoding="utf-8")

    assert "Install-Prerequisites.ps1" in setup
    assert setup.index("Install-Prerequisites.ps1") < setup.index("install-models")
    assert "14.51.36247.0" in prerequisite
    assert "843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c" in prerequisite
    assert "Get-AuthenticodeSignature" in prerequisite
    assert "CN=Microsoft Corporation" in prerequisite
    assert "llama-server.exe" in prerequisite
    assert "'/install', '/quiet', '/norestart'" in prerequisite


def test_llama_cold_start_has_a_vm_tolerant_health_budget() -> None:
    launcher = (
        REPOSITORY_ROOT / "apps" / "launcher" / "src" / "govor_launcher" / "cli.py"
    ).read_text(encoding="utf-8")

    assert "timeout_seconds=180" in launcher
    assert "timeout_seconds: float = 60" in launcher
