from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import uuid
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

PATCH_FORMAT_VERSION = 1
MAX_PATCH_FILES = 20_000
MAX_PATCH_FILE_BYTES = 8 * 1024 * 1024 * 1024
MAX_PATCH_TOTAL_BYTES = 16 * 1024 * 1024 * 1024
PUBLIC_KEY_RELATIVE_PATH = "config/update-signing-public.xml"
PROTECTED_PATHS = frozenset(
    {
        "apply-govor-patch.cmd",
        "apply-govor-patch.ps1",
        PUBLIC_KEY_RELATIVE_PATH,
    }
)

_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RELATIVE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+! /-]{0,239}$")
_WINDOWS_RESERVED_NAME_PATTERN = re.compile(r"^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])$", re.I)
_ANDROID_APPLICATION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")


@dataclass(frozen=True)
class ReleaseMetadata:
    version: str
    android_application_id: str
    android_version_code: int
    android_version_name: str
    android_signer_sha256: str


@dataclass(frozen=True)
class VerifiedPatch:
    manifest: dict[str, object]
    manifest_bytes: bytes


def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{label} fields must be exactly {sorted(expected)}; got {sorted(actual)}")


def _required_string(value: object, label: str, *, maximum: int = 240) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty string no longer than {maximum} characters")
    return value


def _required_integer(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _decode_xml_integer(fields: Mapping[str, str], name: str) -> int:
    encoded = fields.get(name)
    if encoded is None:
        raise ValueError(f"RSA key is missing {name}")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError(f"RSA key {name} is not valid base64") from error
    if not raw:
        raise ValueError(f"RSA key {name} is empty")
    return int.from_bytes(raw, "big")


def _load_xml_fields(path: Path) -> dict[str, str]:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ValueError(f"unable to read RSA key {path}: {error}") from error
    root = re.fullmatch(r"<RSAKeyValue>(.*)</RSAKeyValue>", content)
    if root is None:
        raise ValueError("RSA key root must be RSAKeyValue")
    body = root.group(1)
    matches = list(re.finditer(r"<([A-Za-z]+)>([A-Za-z0-9+/=]+)</\1>", body))
    if not matches or "".join(match.group(0) for match in matches) != body:
        raise ValueError("RSA key contains invalid XML content")
    fields = {match.group(1): match.group(2) for match in matches}
    if len(fields) != len(matches):
        raise ValueError("RSA key contains duplicate fields")
    return fields


def load_public_key(path: Path) -> rsa.RSAPublicKey:
    fields = _load_xml_fields(path)
    if set(fields) != {"Modulus", "Exponent"}:
        raise ValueError("public RSA key must contain only Modulus and Exponent")
    public_key = rsa.RSAPublicNumbers(
        _decode_xml_integer(fields, "Exponent"),
        _decode_xml_integer(fields, "Modulus"),
    ).public_key()
    if public_key.key_size < 3072:
        raise ValueError("application patch RSA keys must be at least 3072 bits")
    return public_key


def load_private_key(path: Path) -> rsa.RSAPrivateKey:
    fields = _load_xml_fields(path)
    expected = {"Modulus", "Exponent", "P", "Q", "DP", "DQ", "InverseQ", "D"}
    if set(fields) != expected:
        raise ValueError("private RSA key has incomplete or unexpected fields")
    public = rsa.RSAPublicNumbers(
        _decode_xml_integer(fields, "Exponent"),
        _decode_xml_integer(fields, "Modulus"),
    )
    private = rsa.RSAPrivateNumbers(
        p=_decode_xml_integer(fields, "P"),
        q=_decode_xml_integer(fields, "Q"),
        d=_decode_xml_integer(fields, "D"),
        dmp1=_decode_xml_integer(fields, "DP"),
        dmq1=_decode_xml_integer(fields, "DQ"),
        iqmp=_decode_xml_integer(fields, "InverseQ"),
        public_numbers=public,
    ).private_key()
    if private.key_size < 3072:
        raise ValueError("application patch RSA keys must be at least 3072 bits")
    return private


def _public_numbers(key: rsa.RSAPublicKey) -> tuple[int, int]:
    numbers = key.public_numbers()
    return numbers.n, numbers.e


def load_release_metadata(root: Path) -> ReleaseMetadata:
    path = root / "config" / "release.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"unable to read release metadata {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("release metadata must be an object")
    _exact_keys(value, {"format_version", "version", "android"}, "release metadata")
    if value["format_version"] != 1:
        raise ValueError("unsupported release metadata format")
    version = _required_string(value["version"], "release version", maximum=80)
    if _SEMVER_PATTERN.fullmatch(version) is None:
        raise ValueError("release version must be semantic")
    android = value["android"]
    if not isinstance(android, dict):
        raise ValueError("release android metadata must be an object")
    _exact_keys(
        android,
        {"application_id", "version_code", "version_name", "signer_sha256"},
        "release android metadata",
    )
    application_id = _required_string(android["application_id"], "Android application ID")
    if _ANDROID_APPLICATION_ID_PATTERN.fullmatch(application_id) is None:
        raise ValueError("Android application ID is invalid")
    version_code = _required_integer(
        android["version_code"], "Android version code", minimum=1, maximum=2_100_000_000
    )
    version_name = _required_string(android["version_name"], "Android version name", maximum=80)
    signer_sha256 = _required_string(
        android["signer_sha256"], "Android signer SHA-256", maximum=64
    ).lower()
    if _SHA256_PATTERN.fullmatch(signer_sha256) is None:
        raise ValueError("Android signer SHA-256 must be 64 lowercase hexadecimal characters")
    return ReleaseMetadata(
        version=version,
        android_application_id=application_id,
        android_version_code=version_code,
        android_version_name=version_name,
        android_signer_sha256=signer_sha256,
    )


def validate_relative_path(value: object) -> str:
    path = _required_string(value, "patch path")
    if (
        _RELATIVE_PATH_PATTERN.fullmatch(path) is None
        or "\\" in path
        or ":" in path
        or path.startswith("/")
    ):
        raise ValueError(f"unsafe patch path: {path!r}")
    parts = PurePosixPath(path).parts
    if any(
        part in {"", ".", ".."}
        or part.endswith((" ", "."))
        or _WINDOWS_RESERVED_NAME_PATTERN.fullmatch(part.split(".", 1)[0]) is not None
        for part in parts
    ):
        raise ValueError(f"unsafe patch path: {path!r}")
    return path


def _validate_digest(value: object, label: str) -> str:
    digest = _required_string(value, label, maximum=64)
    if _SHA256_PATTERN.fullmatch(digest) is None:
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")
    return digest


def validate_manifest(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("patch manifest must be an object")
    _exact_keys(
        value,
        {
            "format_version",
            "patch_id",
            "created_at_utc",
            "from_version",
            "target_version",
            "files",
            "android",
        },
        "patch manifest",
    )
    if value["format_version"] != PATCH_FORMAT_VERSION:
        raise ValueError("unsupported patch format")
    patch_id = _required_string(value["patch_id"], "patch ID", maximum=36)
    try:
        if str(uuid.UUID(patch_id)) != patch_id:
            raise ValueError
    except ValueError as error:
        raise ValueError("patch ID must be a canonical UUID") from error
    created_at = _required_string(value["created_at_utc"], "patch creation time", maximum=40)
    try:
        parsed_created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("patch creation time must be ISO 8601") from error
    if parsed_created_at.tzinfo is None:
        raise ValueError("patch creation time must include a time zone")
    from_version = _required_string(value["from_version"], "source version", maximum=80)
    target_version = _required_string(value["target_version"], "target version", maximum=80)
    if (
        _SEMVER_PATTERN.fullmatch(from_version) is None
        or _SEMVER_PATTERN.fullmatch(target_version) is None
    ):
        raise ValueError("patch versions must be semantic")
    if from_version == target_version:
        raise ValueError("patch target version must differ from its source version")

    files = value["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_PATCH_FILES:
        raise ValueError(f"patch files must contain between one and {MAX_PATCH_FILES} entries")
    paths: set[str] = set()
    total_size = 0
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise ValueError(f"patch file {index} must be an object")
        action = item.get("action")
        if action == "add":
            expected = {"path", "action", "size", "sha256"}
        elif action == "replace":
            expected = {"path", "action", "old_size", "old_sha256", "size", "sha256"}
        elif action == "delete":
            expected = {"path", "action", "old_size", "old_sha256"}
        else:
            raise ValueError(f"patch file {index} has an invalid action")
        _exact_keys(item, expected, f"patch file {index}")
        relative = validate_relative_path(item["path"])
        folded = relative.casefold()
        if folded in paths:
            raise ValueError(f"duplicate patch path: {relative}")
        paths.add(folded)
        if folded in PROTECTED_PATHS:
            raise ValueError(f"patch may not replace protected bootstrap file: {relative}")
        if action in {"replace", "delete"}:
            _required_integer(
                item["old_size"],
                f"patch file {index} old size",
                minimum=0,
                maximum=MAX_PATCH_FILE_BYTES,
            )
            _validate_digest(item["old_sha256"], f"patch file {index} old SHA-256")
        if action in {"add", "replace"}:
            size = _required_integer(
                item["size"],
                f"patch file {index} size",
                minimum=0,
                maximum=MAX_PATCH_FILE_BYTES,
            )
            total_size += size
            _validate_digest(item["sha256"], f"patch file {index} SHA-256")
    android = value["android"]
    if android is not None:
        if not isinstance(android, dict):
            raise ValueError("Android patch metadata must be an object or null")
        _exact_keys(
            android,
            {
                "path",
                "application_id",
                "version_code",
                "version_name",
                "signer_sha256",
                "size",
                "sha256",
            },
            "Android patch metadata",
        )
        android_path = validate_relative_path(android["path"])
        if not android_path.startswith("android/") or not android_path.endswith(".apk"):
            raise ValueError("Android payload must be an APK below android/")
        application_id = _required_string(android["application_id"], "Android application ID")
        if _ANDROID_APPLICATION_ID_PATTERN.fullmatch(application_id) is None:
            raise ValueError("Android application ID is invalid")
        _required_integer(
            android["version_code"],
            "Android version code",
            minimum=1,
            maximum=2_100_000_000,
        )
        _required_string(android["version_name"], "Android version name", maximum=80)
        _validate_digest(android["signer_sha256"], "Android signer SHA-256")
        android_size = _required_integer(
            android["size"],
            "Android APK size",
            minimum=1,
            maximum=MAX_PATCH_FILE_BYTES,
        )
        total_size += android_size
        _validate_digest(android["sha256"], "Android APK SHA-256")
    if total_size > MAX_PATCH_TOTAL_BYTES:
        raise ValueError("patch expanded payload exceeds the total size limit")
    return value


def _regular_files(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"release packages may not contain links: {path}")
        if not path.is_file():
            continue
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError(f"release packages may contain only regular files: {path}")
        relative = path.relative_to(root).as_posix()
        validate_relative_path(relative)
        folded = relative.casefold()
        if folded in result:
            raise ValueError(f"release contains case-colliding paths: {relative}")
        result[folded] = path
    return result


def _file_record(path: Path) -> tuple[int, str]:
    size = path.stat().st_size
    if size > MAX_PATCH_FILE_BYTES:
        raise ValueError(f"release file exceeds patch limit: {path}")
    return size, _sha256_file(path)


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def create_patch(
    base_root: Path,
    target_root: Path,
    output_path: Path,
    private_key_path: Path,
    *,
    android_apk: Path | None = None,
) -> dict[str, object]:
    base_root = base_root.resolve(strict=True)
    target_root = target_root.resolve(strict=True)
    if not base_root.is_dir() or not target_root.is_dir():
        raise ValueError("base and target release paths must be directories")
    base_metadata = load_release_metadata(base_root)
    target_metadata = load_release_metadata(target_root)
    if target_metadata.android_application_id != base_metadata.android_application_id:
        raise ValueError("target Android application ID differs from the base release")
    if target_metadata.android_signer_sha256 != base_metadata.android_signer_sha256:
        raise ValueError("target Android signing identity differs from the base release")
    if target_metadata.android_version_code < base_metadata.android_version_code:
        raise ValueError("target Android version code may not go backwards")
    base_public_path = base_root / PUBLIC_KEY_RELATIVE_PATH
    target_public_path = target_root / PUBLIC_KEY_RELATIVE_PATH
    base_public = load_public_key(base_public_path)
    target_public = load_public_key(target_public_path)
    private = load_private_key(private_key_path.resolve(strict=True))
    if _public_numbers(base_public) != _public_numbers(target_public):
        raise ValueError("base and target releases use different patch signing trust roots")
    if _public_numbers(base_public) != _public_numbers(private.public_key()):
        raise ValueError("patch private key does not match the release trust root")

    base_files = _regular_files(base_root)
    target_files = _regular_files(target_root)
    records: list[dict[str, object]] = []
    payloads: list[tuple[str, Path]] = []
    for folded in sorted(set(base_files) | set(target_files)):
        base = base_files.get(folded)
        target = target_files.get(folded)
        display_path = (target or base).relative_to(target_root if target else base_root).as_posix()  # type: ignore[union-attr]
        if folded in PROTECTED_PATHS:
            if base is None or target is None or base.read_bytes() != target.read_bytes():
                raise ValueError(f"protected patch bootstrap changed: {display_path}")
            continue
        if base is None:
            assert target is not None
            size, digest = _file_record(target)
            records.append({"path": display_path, "action": "add", "size": size, "sha256": digest})
            payloads.append((f"payload/{display_path}", target))
            continue
        old_size, old_digest = _file_record(base)
        if target is None:
            records.append(
                {
                    "path": display_path,
                    "action": "delete",
                    "old_size": old_size,
                    "old_sha256": old_digest,
                }
            )
            continue
        size, digest = _file_record(target)
        if old_size == size and old_digest == digest:
            continue
        records.append(
            {
                "path": display_path,
                "action": "replace",
                "old_size": old_size,
                "old_sha256": old_digest,
                "size": size,
                "sha256": digest,
            }
        )
        payloads.append((f"payload/{display_path}", target))

    android: dict[str, object] | None = None
    if android_apk is not None:
        if target_metadata.android_version_code <= base_metadata.android_version_code:
            raise ValueError(
                "an Android patch requires a target version code greater than the base version code"
            )
        android_apk = android_apk.resolve(strict=True)
        if not android_apk.is_file():
            raise ValueError("Android APK path must be a file")
        size, digest = _file_record(android_apk)
        android_path = f"android/govor.ai-{target_metadata.version}-android-release.apk"
        android = {
            "path": android_path,
            "application_id": target_metadata.android_application_id,
            "version_code": target_metadata.android_version_code,
            "version_name": target_metadata.android_version_name,
            "signer_sha256": target_metadata.android_signer_sha256,
            "size": size,
            "sha256": digest,
        }
        payloads.append((android_path, android_apk))
    if not records:
        raise ValueError("the release directories contain no application changes")

    manifest: dict[str, object] = {
        "format_version": PATCH_FORMAT_VERSION,
        "patch_id": str(uuid.uuid4()),
        "created_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "from_version": base_metadata.version,
        "target_version": target_metadata.version,
        "files": records,
        "android": android,
    }
    validate_manifest(manifest)
    manifest_bytes = _canonical_json(manifest)
    signature = private.sign(manifest_bytes, padding.PKCS1v15(), hashes.SHA256())
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True
        ) as archive:
            archive.writestr("manifest.json", manifest_bytes)
            archive.writestr("manifest.sig", base64.b64encode(signature) + b"\n")
            for archive_path, source in payloads:
                archive.write(source, archive_path)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def verify_patch(patch_path: Path, public_key_path: Path) -> VerifiedPatch:
    public = load_public_key(public_key_path.resolve(strict=True))
    try:
        with zipfile.ZipFile(patch_path.resolve(strict=True)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_PATCH_FILES + 3:
                raise ValueError("patch archive contains too many entries")
            names = [item.filename for item in entries]
            if len(names) != len(set(name.casefold() for name in names)):
                raise ValueError("patch archive contains duplicate or case-colliding entries")
            if archive.getinfo("manifest.json").file_size > 16 * 1024 * 1024:
                raise ValueError("patch manifest exceeds its size limit")
            if archive.getinfo("manifest.sig").file_size > 16 * 1024:
                raise ValueError("patch signature exceeds its size limit")
            manifest_bytes = archive.read("manifest.json")
            signature_text = archive.read("manifest.sig").strip()
            try:
                signature = base64.b64decode(signature_text, validate=True)
            except ValueError as error:
                raise ValueError("patch signature is not valid base64") from error
            try:
                public.verify(signature, manifest_bytes, padding.PKCS1v15(), hashes.SHA256())
            except InvalidSignature as error:
                raise ValueError("application patch signature is invalid") from error
            try:
                manifest_value = json.loads(manifest_bytes)
            except json.JSONDecodeError as error:
                raise ValueError("patch manifest is not valid JSON") from error
            manifest = validate_manifest(manifest_value)
            expected = {"manifest.json", "manifest.sig"}
            files = cast(list[dict[str, object]], manifest["files"])
            for item in files:
                if item["action"] in {"add", "replace"}:
                    expected.add(f"payload/{item['path']}")
            android = manifest["android"]
            if isinstance(android, dict):
                expected.add(str(android["path"]))
            if set(names) != expected:
                raise ValueError("patch archive entries do not exactly match its manifest")
            for item in files:
                if item["action"] not in {"add", "replace"}:
                    continue
                payload_path = f"payload/{item['path']}"
                if archive.getinfo(payload_path).file_size != cast(int, item["size"]):
                    raise ValueError(f"patch payload has the wrong size: {item['path']}")
                payload = archive.read(payload_path)
                if (
                    len(payload) != cast(int, item["size"])
                    or _sha256_bytes(payload) != item["sha256"]
                ):
                    raise ValueError(f"patch payload failed integrity verification: {item['path']}")
            if isinstance(android, dict):
                android_path = str(android["path"])
                if archive.getinfo(android_path).file_size != android["size"]:
                    raise ValueError("Android APK has the wrong size")
                payload = archive.read(android_path)
                if len(payload) != android["size"] or _sha256_bytes(payload) != android["sha256"]:
                    raise ValueError("Android APK failed integrity verification")
    except (KeyError, OSError, zipfile.BadZipFile) as error:
        raise ValueError(f"unable to read application patch: {error}") from error
    return VerifiedPatch(manifest=manifest, manifest_bytes=manifest_bytes)


def _create_command(arguments: argparse.Namespace) -> int:
    manifest = create_patch(
        arguments.base,
        arguments.target,
        arguments.output,
        arguments.private_key,
        android_apk=arguments.android_apk,
    )
    files = cast(list[object], manifest["files"])
    print(
        f"Created signed application patch {arguments.output}: "
        f"{manifest['from_version']} -> {manifest['target_version']}, "
        f"{len(files)} host file operations."
    )
    if manifest["android"] is not None:
        print("The patch also contains the target release Android APK.")
    return 0


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="govor-application-patch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--base", type=Path, required=True)
    create.add_argument("--target", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--private-key", type=Path, required=True)
    create.add_argument("--android-apk", type=Path)
    options = parser.parse_args(arguments)
    if options.command == "create":
        return _create_command(options)
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
