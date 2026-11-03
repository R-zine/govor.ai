from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "packages" / "contracts" / "schemas" / "v1"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "contracts"
LESSON_ROOT = ROOT / "assets" / "lesson-content"


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


@pytest.mark.parametrize("schema_path", sorted(SCHEMA_ROOT.glob("*.schema.json")))
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    Draft202012Validator.check_schema(load_json(schema_path))


def test_default_lesson_files_match_the_versioned_schema() -> None:
    validator = Draft202012Validator(load_json(SCHEMA_ROOT / "lesson-definition.schema.json"))
    lesson_paths = sorted(LESSON_ROOT.glob("*.json"))

    assert len(lesson_paths) == 4
    for lesson_path in lesson_paths:
        validator.validate(load_json(lesson_path))


@pytest.mark.parametrize(
    ("schema_name", "fixture_name"),
    [
        ("message-envelope.schema.json", "message-envelope.json"),
        ("signaling-message.schema.json", "signaling-offer.json"),
        ("gateway-auth-message.schema.json", "gateway-pairing-request.json"),
        ("gateway-auth-message.schema.json", "gateway-auth-request.json"),
        ("pairing-bootstrap.schema.json", "pairing-bootstrap.json"),
        ("control-message.schema.json", "control-teacher-turn.json"),
        ("control-message.schema.json", "control-word-replay-request.json"),
        ("control-message.schema.json", "control-word-audio.json"),
        ("control-message.schema.json", "control-lesson-catalog.json"),
        ("control-message.schema.json", "control-lesson-create-request.json"),
        ("control-message.schema.json", "control-lesson-create-result.json"),
        ("control-message.schema.json", "control-lesson-create-failed.json"),
        ("control-message.schema.json", "control-renderer-command.json"),
        ("control-message.schema.json", "control-teacher-profile-selected.json"),
        ("control-message.schema.json", "control-teacher-profile-select.json"),
        ("control-message.schema.json", "control-custom-scene.json"),
        ("environment-definition.schema.json", "environment-hotel-lobby.json"),
        ("application-patch-manifest.schema.json", "application-patch-manifest.json"),
        ("local-ai-dialogue.schema.json", "local-ai-dialogue.json"),
        ("local-ai-lesson-content.schema.json", "local-ai-lesson-content.json"),
    ],
)
def test_positive_contract_fixtures(schema_name: str, fixture_name: str) -> None:
    validator = Draft202012Validator(
        load_json(SCHEMA_ROOT / schema_name), format_checker=FormatChecker()
    )
    validator.validate(load_json(FIXTURE_ROOT / "valid" / fixture_name))


@pytest.mark.parametrize(
    ("schema_name", "fixture_name"),
    [
        ("message-envelope.schema.json", "message-envelope-missing-correlation.json"),
        ("signaling-message.schema.json", "signaling-unknown-field.json"),
        ("gateway-auth-message.schema.json", "gateway-pairing-code-invalid.json"),
        ("pairing-bootstrap.schema.json", "pairing-bootstrap-extra-field.json"),
        ("control-message.schema.json", "control-recording-extra-field.json"),
        ("control-message.schema.json", "control-lesson-progress-invalid.json"),
        ("control-message.schema.json", "control-lesson-create-blank-topic.json"),
        ("control-message.schema.json", "control-scene-arbitrary-asset.json"),
        ("local-ai-dialogue.schema.json", "local-ai-control-injection.json"),
        ("local-ai-lesson-content.schema.json", "local-ai-lesson-command.json"),
        ("application-patch-manifest.schema.json", "application-patch-path-traversal.json"),
    ],
)
def test_negative_contract_fixtures(schema_name: str, fixture_name: str) -> None:
    validator = Draft202012Validator(
        load_json(SCHEMA_ROOT / schema_name), format_checker=FormatChecker()
    )
    with pytest.raises(ValidationError):
        validator.validate(load_json(FIXTURE_ROOT / "invalid" / fixture_name))
