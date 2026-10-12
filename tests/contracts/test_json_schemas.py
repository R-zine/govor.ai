from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "packages" / "contracts" / "schemas" / "v1"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "contracts"


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


@pytest.mark.parametrize("schema_path", sorted(SCHEMA_ROOT.glob("*.schema.json")))
def test_schema_is_valid_draft_2020_12(schema_path: Path) -> None:
    Draft202012Validator.check_schema(load_json(schema_path))


@pytest.mark.parametrize(
    ("schema_name", "fixture_name"),
    [
        ("message-envelope.schema.json", "message-envelope.json"),
        ("signaling-message.schema.json", "signaling-offer.json"),
        ("control-message.schema.json", "control-teacher-turn.json"),
        ("control-message.schema.json", "control-word-replay-request.json"),
        ("control-message.schema.json", "control-word-audio.json"),
        ("control-message.schema.json", "control-renderer-command.json"),
        ("local-ai-dialogue.schema.json", "local-ai-dialogue.json"),
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
        ("control-message.schema.json", "control-recording-extra-field.json"),
        ("control-message.schema.json", "control-lesson-progress-invalid.json"),
        ("control-message.schema.json", "control-scene-arbitrary-asset.json"),
        ("local-ai-dialogue.schema.json", "local-ai-control-injection.json"),
    ],
)
def test_negative_contract_fixtures(schema_name: str, fixture_name: str) -> None:
    validator = Draft202012Validator(
        load_json(SCHEMA_ROOT / schema_name), format_checker=FormatChecker()
    )
    with pytest.raises(ValidationError):
        validator.validate(load_json(FIXTURE_ROOT / "invalid" / fixture_name))
