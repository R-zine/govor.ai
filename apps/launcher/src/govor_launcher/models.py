from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

import certifi

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class ModelArtifact:
    id: str
    display_name: str
    relative_path: str
    uri: str
    sha256: str
    size: int
    license: str
    source_revision: str

    @classmethod
    def parse(cls, value: object) -> ModelArtifact:
        if not isinstance(value, dict):
            raise ValueError("model manifest entries must be objects")
        required = {
            "id",
            "display_name",
            "relative_path",
            "uri",
            "sha256",
            "size",
            "license",
            "source_revision",
        }
        if set(value) != required:
            raise ValueError("model manifest entry has missing or unknown fields")
        artifact = cls(**value)
        path = PurePosixPath(artifact.relative_path)
        if not _ID_PATTERN.fullmatch(artifact.id):
            raise ValueError("model ID is invalid")
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError("model path must stay below the model directory")
        parsed_uri = urlparse(artifact.uri)
        if parsed_uri.scheme != "https" or not parsed_uri.hostname:
            raise ValueError("model URI must use HTTPS")
        if not _SHA256_PATTERN.fullmatch(artifact.sha256):
            raise ValueError("model SHA-256 is invalid")
        if not isinstance(artifact.size, int) or artifact.size <= 0:
            raise ValueError("model size must be a positive integer")
        for text in (
            artifact.display_name,
            artifact.license,
            artifact.source_revision,
        ):
            if not isinstance(text, str) or not 1 <= len(text) <= 128:
                raise ValueError("model manifest text is invalid")
        return artifact


def load_manifest(path: str | Path) -> tuple[ModelArtifact, ...]:
    try:
        value: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("model manifest is unreadable") from error
    if not isinstance(value, dict) or set(value) != {"manifest_version", "models"}:
        raise ValueError("model manifest has an invalid root")
    if value["manifest_version"] != 1 or not isinstance(value["models"], list):
        raise ValueError("model manifest version is unsupported")
    artifacts = tuple(ModelArtifact.parse(item) for item in value["models"])
    if len({artifact.id for artifact in artifacts}) != len(artifacts):
        raise ValueError("model IDs must be unique")
    if len({artifact.relative_path for artifact in artifacts}) != len(artifacts):
        raise ValueError("model paths must be unique")
    return artifacts


def artifact_path(model_root: Path, artifact: ModelArtifact) -> Path:
    resolved_root = model_root.resolve()
    candidate = (resolved_root / Path(*PurePosixPath(artifact.relative_path).parts)).resolve()
    if resolved_root not in candidate.parents:
        raise ValueError("model path escaped the model directory")
    return candidate


def verify_artifact(path: Path, artifact: ModelArtifact) -> str:
    if not path.is_file():
        return "missing"
    if path.stat().st_size != artifact.size:
        return "size_mismatch"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "ready" if hmac_compare(digest.hexdigest(), artifact.sha256) else "hash_mismatch"


def install_artifact(model_root: Path, artifact: ModelArtifact) -> Path:
    destination = artifact_path(model_root, artifact)
    if verify_artifact(destination, artifact) == "ready":
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{secrets.token_hex(8)}.partial")
    request = urllib.request.Request(  # noqa: S310 - manifest validation requires HTTPS
        artifact.uri,
        headers={"User-Agent": "govor.ai-model-setup/0.1"},
    )
    digest = hashlib.sha256()
    count = 0
    try:
        import ssl

        context = ssl.create_default_context(cafile=certifi.where())
        with (
            urllib.request.urlopen(  # noqa: S310 - request URL was constrained to HTTPS
                request, timeout=60, context=context
            ) as response,
            temporary.open("wb") as output,
        ):
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > artifact.size:
                    raise ValueError(f"{artifact.display_name} exceeded its pinned size")
                digest.update(block)
                output.write(block)
        if count != artifact.size:
            raise ValueError(
                f"{artifact.display_name} size mismatch: expected {artifact.size}, received {count}"
            )
        if not hmac_compare(digest.hexdigest(), artifact.sha256):
            raise ValueError(f"{artifact.display_name} failed its SHA-256 integrity check")
        os.replace(temporary, destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def hmac_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)
