from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pre-commit-tests.ps1"
SYNTAX_SCRIPT = ROOT / "scripts" / "check-powershell-syntax.ps1"
POWERSHELL = shutil.which("powershell.exe")
GIT = shutil.which("git")


@pytest.mark.parametrize(
    ("paths", "expected_scopes"),
    [
        (("apps/host/src/govor_host/app.py",), "python"),
        (("apps/android/app/src/main/kotlin/Test.kt",), "kotlin"),
        (("apps/android/gradle/libs.versions.toml",), "kotlin"),
        (("apps/renderer/Scripts/RendererRoot.cs",), "godot"),
        (("apps/renderer/Assets/Backdrops/cafe.jpg",), "godot"),
        (("packages/contracts/csharp/Contract.cs",), "csharp,godot"),
        (("packages/contracts/csharp/Govor.Contracts.Tests/Example.cs",), "csharp"),
        (("packages/contracts/schemas/v1/control-message.schema.json",), "all"),
        (("packages/contracts/python/govor_contracts/models.py",), "python,media"),
        (("packages/gateway_security/src/govor_gateway_security/authority.py",), "python,media"),
        (("services/media/src/media.py", "services/speech/src/speech.py"), "python,media"),
        (("docs/architecture/overview.md",), ""),
        ((".gitignore", ".editorconfig"), ""),
        (("README.md", "COPYRIGHT", "LICENSE", "licenses/third-party/example.txt"), ""),
        (("apps/android/README.md", "apps/renderer/README.md"), ""),
        ((".pre-commit-config.yaml",), "all"),
        ((".github/workflows/ci.yml",), "all"),
        (("scripts/test.ps1",), "all"),
        (("tests/integration/test_pre_commit_dispatch.py",), "all"),
        (("apps/host/tests/conftest.py",), "all"),
        (("uv.lock",), "all"),
        (("new-component/runtime.txt",), "all"),
        ((".\\APPS\\ANDROID\\app\\src\\Example.kt",), "kotlin"),
        (("services/media/tests/test_peer.py",), "media"),
        ((), ""),
    ],
)
def test_pre_commit_dispatches_affected_software_suites(
    paths: tuple[str, ...],
    expected_scopes: str,
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

    plan = dict(line.split(": ", 1) for line in result.stdout.splitlines())
    assert plan["Scopes"] == expected_scopes
    assert plan["DependencyAudit"] == str("uv.lock" in paths).lower()


@pytest.mark.parametrize(
    ("path", "expected_tests"),
    [
        (
            "apps/host/src/govor_host/app.py",
            {"apps/host/tests", "tests/integration/test_mock_lesson.py"},
        ),
        (
            "apps/host/src/govor_host/config.py",
            {
                "apps/host/tests",
                "services/provider_router/tests",
                "tests/integration/test_mock_lesson.py",
            },
        ),
        ("apps/launcher/src/govor_launcher/cli.py", {"apps/launcher/tests"}),
        (
            "packages/scene_planner/src/govor_scene_planner/scenes.py",
            {
                "packages/scene_planner/tests",
                "apps/host/tests",
                "apps/launcher/tests",
                "tests/integration/test_mock_lesson.py",
            },
        ),
        (
            "services/speech/src/govor_speech/providers.py",
            {
                "services/speech/tests",
                "services/local_ai/tests",
                "services/provider_router/tests",
                "apps/host/tests",
                "apps/launcher/tests",
                "tests/integration/test_mock_lesson.py",
            },
        ),
        ("services/speech/tests/test_speech.py", {"services/speech/tests"}),
        ("scripts/package.ps1", {"apps/launcher/tests"}),
        ("distribution/windows/Apply-Govor-Patch.ps1", {"apps/launcher/tests"}),
        ("config/release-models.json", {"apps/launcher/tests"}),
        ("config/m8-vm.json", {"tests/integration/test_m8_vm_fixture.py"}),
        ("scripts/m8-vm.ps1", {"tests/integration/test_m8_vm_fixture.py"}),
        ("tests/integration/test_removed.py", {"tests/integration"}),
    ],
)
def test_python_selection_covers_consumers_without_unrelated_suites(
    path: str, expected_tests: set[str]
) -> None:
    result = run_dispatcher(SCRIPT, "-ListOnly", path)
    assert result.returncode == 0, result.stderr
    plan = dict(line.split(": ", 1) for line in result.stdout.splitlines())
    assert set(plan["PythonTests"].split(",")) == expected_tests
    assert plan["Scopes"] == "python"


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("govor_domain", "packages/domain/src"),
        ("govor_provider_interfaces", "packages/provider_interfaces/src"),
        ("govor_gateway_security", "packages/gateway_security/src"),
        ("govor_progress", "packages/progress/src"),
        ("govor_scene_planner", "packages/scene_planner/src"),
        ("govor_speech", "services/speech/src"),
        ("govor_local_ai", "services/local_ai/src"),
        ("govor_provider_router", "services/provider_router/src"),
    ],
)
def test_component_map_covers_actual_cross_component_imports(module: str, source: str) -> None:
    # Inspect real imports, including imports inside functions, rather than mirroring the
    # dispatcher's dependency table. New runtime consumers must be added to that table.
    result = run_dispatcher(SCRIPT, "-ListOnly", f"{source}/{module}/__init__.py")
    assert result.returncode == 0, result.stderr
    plan = dict(line.split(": ", 1) for line in result.stdout.splitlines())
    selected = set(plan["PythonTests"].split(","))
    for parent in ("apps", "packages", "services"):
        for src in (ROOT / parent).glob("*/src"):
            tests = src.parent / "tests"
            if not tests.is_dir() or src == ROOT / source:
                continue
            for path in src.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                        imports.add(node.module.split(".")[0])
                    elif isinstance(node, ast.Import):
                        imports.update(alias.name.split(".")[0] for alias in node.names)
                if module in imports:
                    suite = tests.relative_to(ROOT).as_posix()
                    if suite == "services/media/tests":
                        assert "media" in plan["Scopes"].split(",")
                    else:
                        assert suite in selected, f"{module} can affect {path.relative_to(ROOT)}"


def run_dispatcher(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    if POWERSHELL is None:
        pytest.skip("the staged-test dispatcher is Windows-local")
    return subprocess.run(  # noqa: S603 - repository-owned script and test paths
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        cwd=script.parent.parent,
        check=False,
        capture_output=True,
        text=True,
        env=isolated_git_environment(),
    )


def isolated_git_environment() -> dict[str, str]:
    # git commit can export its real/alternate index and working tree to hooks. Temporary test
    # repositories must never inherit those paths or inspect/mutate the caller's repository.
    return {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}


@pytest.fixture
def isolated_dispatcher(tmp_path: Path) -> Path:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    copied_script = scripts / SCRIPT.name
    shutil.copyfile(SCRIPT, copied_script)
    (scripts / "test.ps1").write_text(
        "param([string]$Scope, [string[]]$PythonTestPaths)\n"
        "@{scope=$Scope; tests=@($PythonTestPaths)} | ConvertTo-Json -Compress | "
        "Add-Content -LiteralPath (Join-Path $PSScriptRoot 'calls.jsonl')\n"
        "if (Test-Path (Join-Path $PSScriptRoot 'fail')) { exit 7 }\n"
        "exit 0\n",
        encoding="utf-8",
    )
    return copied_script


def test_selected_scopes_run_once_and_pass_python_test_arguments(isolated_dispatcher: Path) -> None:
    result = run_dispatcher(
        isolated_dispatcher,
        "apps/host/src/govor_host/app.py",
        "services/media/src/govor_media/peer.py",
        "apps/host/src/govor_host/app.py",
        "scripts/progress.ps1",
    )
    assert result.returncode == 0, result.stderr
    calls = [
        json.loads(line)
        for line in (isolated_dispatcher.parent / "calls.jsonl").read_text().splitlines()
    ]
    assert [call["scope"] for call in calls] == ["python", "media"]
    assert set(calls[0]["tests"]) == {
        "apps/host/tests",
        "tests/integration/test_mock_lesson.py",
    }


def test_a_failed_suite_rejects_the_commit_and_stops_later_suites(
    isolated_dispatcher: Path,
) -> None:
    (isolated_dispatcher.parent / "fail").touch()
    result = run_dispatcher(
        isolated_dispatcher,
        "apps/host/src/govor_host/app.py",
        "services/media/src/govor_media/peer.py",
    )
    assert result.returncode != 0
    assert "Affected test scope 'python' failed" in result.stderr
    calls = (isolated_dispatcher.parent / "calls.jsonl").read_text().splitlines()
    assert len(calls) == 1
    assert "Affected tests passed" not in result.stdout


def git(root: Path, *args: str) -> None:
    if GIT is None:
        pytest.skip("Git is needed for staged-path integration tests")
    subprocess.run(  # noqa: S603 - fixed Git commands in an isolated test repository
        [GIT, "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env=isolated_git_environment(),
    )


@pytest.mark.parametrize("rename", [False, True])
def test_staged_deletions_and_renames_include_the_original_component(
    isolated_dispatcher: Path, rename: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = isolated_dispatcher.parent.parent
    monkeypatch.setenv("GIT_DIR", str(root / "foreign" / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(root / "foreign" / "index"))
    old_path = root / "apps/android/old name.kt"
    old_path.parent.mkdir(parents=True)
    old_path.write_text("// fixture\n", encoding="utf-8")
    git(root, "init")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Hook test",
        "-c",
        "user.email=hook@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-verify",
        "-m",
        "fixture",
    )
    if rename:
        new_path = root / "apps/renderer/moved name.cs"
        new_path.parent.mkdir(parents=True)
        old_path.rename(new_path)
        git(root, "add", "-A")
    else:
        old_path.unlink()
        git(root, "add", "-u")

    result = run_dispatcher(isolated_dispatcher, "-Staged", "-ListOnly")
    assert result.returncode == 0, result.stderr
    plan = dict(line.split(": ", 1) for line in result.stdout.splitlines())
    assert plan["Scopes"] == ("kotlin,godot" if rename else "kotlin")
    assert not (root / "foreign").exists()


def test_index_failure_does_not_silently_skip_checks(isolated_dispatcher: Path) -> None:
    result = run_dispatcher(isolated_dispatcher, "-Staged", "-ListOnly")
    assert result.returncode != 0
    assert "Cannot inspect staged paths" in result.stderr


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
