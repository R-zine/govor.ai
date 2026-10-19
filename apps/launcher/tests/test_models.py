from __future__ import annotations

import hashlib
import io
import json

import pytest
from govor_launcher.models import (
    ModelArtifact,
    artifact_path,
    install_artifact,
    load_manifest,
    verify_artifact,
)


def artifact(**changes: object) -> ModelArtifact:
    content = b"model-data"
    values: dict[str, object] = {
        "id": "test-model",
        "display_name": "Test model",
        "relative_path": "test/model.bin",
        "uri": "https://models.example/model.bin",
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
        "license": "MIT",
        "source_revision": "revision-1",
    }
    values.update(changes)
    return ModelArtifact.parse(values)


def test_repository_release_manifest_is_valid() -> None:
    models = load_manifest("config/release-models.json")

    assert len(models) == 6
    assert {model.license for model in models} == {"Apache-2.0", "MIT", "CC0-1.0"}


def test_model_integrity_requires_size_and_hash(tmp_path) -> None:
    model = artifact()
    path = artifact_path(tmp_path, model)
    assert verify_artifact(path, model) == "missing"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"short")
    assert verify_artifact(path, model) == "size_mismatch"
    path.write_bytes(b"model-datx")
    assert verify_artifact(path, model) == "hash_mismatch"
    path.write_bytes(b"model-data")
    assert verify_artifact(path, model) == "ready"


def test_manifest_rejects_traversal_and_unknown_fields(tmp_path) -> None:
    with pytest.raises(ValueError, match="below the model"):
        artifact(relative_path="../escape.bin")

    manifest = tmp_path / "models.json"
    manifest.write_text(
        json.dumps({"manifest_version": 1, "models": [{"unexpected": True}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing or unknown"):
        load_manifest(manifest)


def test_model_install_streams_to_verified_atomic_destination(tmp_path, monkeypatch) -> None:
    content = b"model-data"
    model = artifact()
    monkeypatch.setattr(
        "govor_launcher.models.urllib.request.urlopen",
        lambda *args, **kwargs: io.BytesIO(content),
    )

    destination = install_artifact(tmp_path, model)

    assert destination.read_bytes() == content
    assert install_artifact(tmp_path, model) == destination
    assert list(destination.parent.glob("*.partial")) == []


def test_model_install_rejects_unpinned_content(tmp_path, monkeypatch) -> None:
    model = artifact()
    monkeypatch.setattr(
        "govor_launcher.models.urllib.request.urlopen",
        lambda *args, **kwargs: io.BytesIO(b"model-datx"),
    )

    with pytest.raises(ValueError, match="integrity"):
        install_artifact(tmp_path, model)
    assert not artifact_path(tmp_path, model).exists()
