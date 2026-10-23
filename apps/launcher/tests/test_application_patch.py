from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from govor_launcher.application_patch import create_patch, validate_relative_path, verify_patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SIGNER_DIGEST = "ab" * 32


def _xml_integer(value: int) -> str:
    encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.b64encode(encoded).decode()


def _powershell() -> str:
    executable = shutil.which("powershell.exe")
    assert executable is not None
    return executable


def _write_key_pair(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    numbers = key.private_numbers()
    fields = {
        "Modulus": numbers.public_numbers.n,
        "Exponent": numbers.public_numbers.e,
        "P": numbers.p,
        "Q": numbers.q,
        "DP": numbers.dmp1,
        "DQ": numbers.dmq1,
        "InverseQ": numbers.iqmp,
        "D": numbers.d,
    }
    private = root / "private.xml"
    public = root / "public.xml"
    private.write_text(
        "<RSAKeyValue>"
        + "".join(f"<{name}>{_xml_integer(value)}</{name}>" for name, value in fields.items())
        + "</RSAKeyValue>\n",
        encoding="utf-8",
    )
    public.write_text(
        "<RSAKeyValue>"
        f"<Modulus>{_xml_integer(numbers.public_numbers.n)}</Modulus>"
        f"<Exponent>{_xml_integer(numbers.public_numbers.e)}</Exponent>"
        "</RSAKeyValue>\n",
        encoding="utf-8",
    )
    return private, public


def _write_release(root: Path, version: str, version_code: int, public_key: Path) -> None:
    config = root / "config"
    config.mkdir(parents=True)
    shutil.copyfile(public_key, config / "update-signing-public.xml")
    (config / "release.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "version": version,
                "android": {
                    "application_id": "ai.govor.app",
                    "version_code": version_code,
                    "version_name": version,
                    "signer_sha256": SIGNER_DIGEST,
                },
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def patch_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    private, public = _write_key_pair(tmp_path)
    base = tmp_path / "base"
    target = tmp_path / "target"
    _write_release(base, "1.0.0", 1, public)
    _write_release(target, "1.1.0", 2, public)
    (base / "app").mkdir()
    (target / "app").mkdir()
    (base / "app" / "replace.txt").write_text("old\n", encoding="utf-8")
    (target / "app" / "replace.txt").write_text("new\n", encoding="utf-8")
    (base / "app" / "delete.txt").write_text("remove\n", encoding="utf-8")
    (target / "app" / "add.txt").write_text("added\n", encoding="utf-8")
    apk = tmp_path / "govor.apk"
    apk.write_bytes(b"fixture signed apk")
    return base, target, private, public, apk


def test_create_and_verify_patch_covers_host_operations_and_android(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, public, apk = patch_fixture
    output = tmp_path / "update.govorpatch"
    runtime_library = target / "runtime" / "python" / "Lib" / "site-packages" / "av.libs"
    runtime_library.mkdir(parents=True)
    (runtime_library / "libstdc++-fixture.dll").write_bytes(b"runtime library")
    voice = target / "runtime" / "voices" / "!v"
    voice.mkdir(parents=True)
    (voice / "Mr serious").write_text("voice fixture\n", encoding="utf-8")

    manifest = create_patch(base, target, output, private, android_apk=apk)
    verified = verify_patch(output, public)

    assert verified.manifest == manifest
    assert {item["action"] for item in manifest["files"]} == {"add", "replace", "delete"}
    assert {
        "runtime/python/Lib/site-packages/av.libs/libstdc++-fixture.dll",
        "runtime/voices/!v/Mr serious",
    }.issubset({item["path"] for item in manifest["files"]})
    assert manifest["android"] == {
        "path": "android/govor.ai-1.1.0-android-release.apk",
        "application_id": "ai.govor.app",
        "version_code": 2,
        "version_name": "1.1.0",
        "signer_sha256": SIGNER_DIGEST,
        "size": len(b"fixture signed apk"),
        "sha256": hashlib.sha256(b"fixture signed apk").hexdigest(),
    }


def test_verifier_rejects_a_payload_changed_after_signing(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, public, _ = patch_fixture
    original = tmp_path / "original.govorpatch"
    altered = tmp_path / "altered.govorpatch"
    create_patch(base, target, original, private)

    with zipfile.ZipFile(original) as source, zipfile.ZipFile(altered, "w") as destination:
        for entry in source.infolist():
            payload = source.read(entry.filename)
            if entry.filename.endswith("app/add.txt"):
                payload = b"evil!\r\n"
            destination.writestr(entry.filename, payload)

    with pytest.raises(ValueError, match="integrity verification"):
        verify_patch(altered, public)


def test_verifier_rejects_a_different_signing_identity(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, _, _ = patch_fixture
    output = tmp_path / "update.govorpatch"
    _, unrelated_public = _write_key_pair(tmp_path / "unrelated")
    create_patch(base, target, output, private)

    with pytest.raises(ValueError, match="signature is invalid"):
        verify_patch(output, unrelated_public)


@pytest.mark.parametrize(
    "path",
    [
        "runtime/CON.txt",
        "runtime/com1/config.json",
        "runtime/name. ",
        "runtime/name.",
    ],
)
def test_path_validation_rejects_windows_aliases_and_normalization_collisions(path: str) -> None:
    with pytest.raises(ValueError, match="unsafe patch path"):
        validate_relative_path(path)


def test_creator_refuses_to_replace_the_bootstrap_or_trust_key(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, _, _ = patch_fixture
    (base / "Apply-Govor-Patch.ps1").write_text("stable", encoding="utf-8")
    (target / "Apply-Govor-Patch.ps1").write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="protected patch bootstrap changed"):
        create_patch(base, target, tmp_path / "update.govorpatch", private)


def test_creator_refuses_an_android_signing_identity_change(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, _, _ = patch_fixture
    release_path = target / "config" / "release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["android"]["signer_sha256"] = "cd" * 32
    release_path.write_text(json.dumps(release), encoding="utf-8")

    with pytest.raises(ValueError, match="signing identity differs"):
        create_patch(base, target, tmp_path / "update.govorpatch", private)


@pytest.mark.skipif(os.name != "nt", reason="the release script is Windows-only")
def test_release_script_creates_a_verifiable_patch(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, public, apk = patch_fixture
    output = tmp_path / "script-created.govorpatch"

    result = subprocess.run(  # noqa: S603 - fixed OS executable and repository-owned script
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPOSITORY_ROOT / "scripts" / "create-application-patch.ps1"),
            "-BasePackagePath",
            str(base),
            "-TargetPackagePath",
            str(target),
            "-PrivateKeyPath",
            str(private),
            "-AndroidApkPath",
            str(apk),
            "-OutputPath",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert verify_patch(output, public).manifest["target_version"] == "1.1.0"
    assert "Created signed application patch" in result.stdout


@pytest.mark.skipif(os.name != "nt", reason="the packaged updater is Windows-only")
def test_windows_updater_applies_a_signed_patch_and_preserves_untracked_content(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, _, apk = patch_fixture
    runtime_library = target / "runtime" / "python" / "Lib" / "site-packages" / "av.libs"
    runtime_library.mkdir(parents=True)
    (runtime_library / "libstdc++-fixture.dll").write_bytes(b"runtime library")
    voice = target / "runtime" / "voices" / "!v"
    voice.mkdir(parents=True)
    (voice / "Mr serious").write_text("voice fixture\n", encoding="utf-8")
    output = tmp_path / "update.govorpatch"
    create_patch(base, target, output, private, android_apk=apk)
    custom = base / "content" / "lessons" / "my-local-lesson.json"
    custom.parent.mkdir(parents=True)
    custom.write_text("{}\n", encoding="utf-8")
    data_root = tmp_path / "data"
    environment = os.environ.copy()
    environment["GOVOR_DATA_ROOT"] = str(data_root)
    result = subprocess.run(  # noqa: S603 - fixed OS executable and repository-owned script
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPOSITORY_ROOT / "distribution" / "windows" / "Apply-Govor-Patch.ps1"),
            "-InstallRoot",
            str(base),
            "-PatchPath",
            str(output),
            "-NoPrompt",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (base / "app" / "replace.txt").read_text(encoding="utf-8") == "new\n"
    assert (base / "app" / "add.txt").read_text(encoding="utf-8") == "added\n"
    assert (base / runtime_library.relative_to(target) / "libstdc++-fixture.dll").read_bytes() == (
        b"runtime library"
    )
    assert (base / voice.relative_to(target) / "Mr serious").read_text(encoding="utf-8") == (
        "voice fixture\n"
    )
    assert not (base / "app" / "delete.txt").exists()
    assert custom.is_file()
    assert json.loads((base / "config" / "release.json").read_text())["version"] == "1.1.0"
    installed_apk = data_root / "updates" / "android" / "govor.ai-1.1.0-android-release.apk"
    assert installed_apk.read_bytes() == b"fixture signed apk"
    assert "Installed signed govor.ai application patch: 1.0.0 -> 1.1.0" in result.stdout


@pytest.mark.skipif(os.name != "nt", reason="the packaged updater is Windows-only")
def test_windows_updater_rolls_back_when_a_late_operation_cannot_commit(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, _, _ = patch_fixture
    late_target = target / "zzz" / "late.txt"
    late_target.parent.mkdir()
    late_target.write_text("late operation\n", encoding="utf-8")
    output = tmp_path / "rollback.govorpatch"
    create_patch(base, target, output, private)
    # This untracked parent-file collision passes the complete-file preflight but prevents the
    # alphabetically late add from creating its parent directory after earlier operations commit.
    (base / "zzz").write_text("local parent collision\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["GOVOR_DATA_ROOT"] = str(tmp_path / "data")

    result = subprocess.run(  # noqa: S603 - fixed OS executable and repository-owned script
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPOSITORY_ROOT / "distribution" / "windows" / "Apply-Govor-Patch.ps1"),
            "-InstallRoot",
            str(base),
            "-PatchPath",
            str(output),
            "-NoPrompt",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode != 0
    assert "all committed host changes were rolled back" in result.stdout + result.stderr
    assert (base / "app" / "replace.txt").read_text(encoding="utf-8") == "old\n"
    assert (base / "app" / "delete.txt").read_text(encoding="utf-8") == "remove\n"
    assert not (base / "app" / "add.txt").exists()
    assert (base / "zzz").read_text(encoding="utf-8") == "local parent collision\n"
    assert json.loads((base / "config" / "release.json").read_text())["version"] == "1.0.0"


@pytest.mark.skipif(os.name != "nt", reason="the packaged updater is Windows-only")
def test_windows_updater_rejects_tampered_payload_before_mutation(
    patch_fixture: tuple[Path, Path, Path, Path, Path], tmp_path: Path
) -> None:
    base, target, private, _, _ = patch_fixture
    original = tmp_path / "original.govorpatch"
    altered = tmp_path / "altered.govorpatch"
    create_patch(base, target, original, private)
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(altered, "w") as destination:
        for entry in source.infolist():
            payload = source.read(entry.filename)
            if entry.filename.endswith("app/add.txt"):
                payload = b"evil!\r\n"
            destination.writestr(entry.filename, payload)
    environment = os.environ.copy()
    environment["GOVOR_DATA_ROOT"] = str(tmp_path / "data")

    result = subprocess.run(  # noqa: S603 - fixed OS executable and repository-owned script
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPOSITORY_ROOT / "distribution" / "windows" / "Apply-Govor-Patch.ps1"),
            "-InstallRoot",
            str(base),
            "-PatchPath",
            str(altered),
            "-NoPrompt",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode != 0
    assert "failed SHA-256 verification" in result.stdout + result.stderr
    assert (base / "app" / "replace.txt").read_text(encoding="utf-8") == "old\n"
    assert (base / "app" / "delete.txt").is_file()
    assert not (base / "app" / "add.txt").exists()
    assert json.loads((base / "config" / "release.json").read_text())["version"] == "1.0.0"
