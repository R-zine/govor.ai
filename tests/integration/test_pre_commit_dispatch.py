from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pre-commit-tests.ps1"
SYNTAX_SCRIPT = ROOT / "scripts" / "check-powershell-syntax.ps1"
POWERSHELL = shutil.which("powershell.exe")


@pytest.mark.parametrize(
    ("paths", "expected_scopes", "expected_android_build"),
    [
        (("apps/host/src/govor_host/app.py",), "python", "false"),
        (("apps/android/app/src/main/kotlin/Test.kt",), "kotlin", "true"),
        (("apps/renderer/Scripts/RendererRoot.cs",), "godot", "false"),
        (("packages/contracts/csharp/Contract.cs",), "csharp,godot", "false"),
        (("packages/contracts/schemas/v1/control-message.schema.json",), "all", "false"),
        (("services/media/src/media.py", "services/speech/src/speech.py"), "media,speech", "false"),
        (("docs/architecture/overview.md",), "", "false"),
        ((".pre-commit-config.yaml",), "all", "false"),
    ],
)
def test_pre_commit_dispatches_affected_software_suites(
    paths: tuple[str, ...],
    expected_scopes: str,
    expected_android_build: str,
) -> None:
    if POWERSHELL is None:
        pytest.skip("the staged-test dispatcher is Windows-local")
    result = subprocess.run(  # noqa: S603 - fixed repository-owned script and arguments
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-ListOnly",
            *paths,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"Scopes: {expected_scopes}" in result.stdout
    assert f"AndroidBuild: {expected_android_build}" in result.stdout


def test_powershell_syntax_hook_accepts_valid_and_rejects_invalid_files(tmp_path: Path) -> None:
    if POWERSHELL is None:
        pytest.skip("the PowerShell syntax hook is Windows-local")
    invalid = tmp_path / "invalid.ps1"
    invalid.write_text("if ($true) {\n", encoding="utf-8")

    valid_result = subprocess.run(  # noqa: S603 - fixed repository-owned script and arguments
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SYNTAX_SCRIPT),
            str(SCRIPT),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    invalid_result = subprocess.run(  # noqa: S603 - fixed repository-owned script and arguments
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SYNTAX_SCRIPT),
            str(invalid),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert valid_result.returncode == 0
    assert "PowerShell syntax passed." in valid_result.stdout
    assert invalid_result.returncode == 1
    assert "Missing closing '}'" in invalid_result.stdout
