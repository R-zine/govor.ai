from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from govor_launcher.pairing_qr import build_pairing_bootstrap, write_pairing_qr


def test_pairing_bootstrap_is_a_strict_versioned_envelope(tmp_path: Path) -> None:
    value = build_pairing_bootstrap(
        control_host="192.168.100.72:8765",
        media_host="192.168.100.72:8766",
        pairing_code="12345678",
        certificate_sha256="A" * 64,
        expires_at_unix=1_792_931_082,
        correlation_id=UUID("9a352221-6fbd-4dd0-9fee-d14a07998d72"),
    )

    envelope = json.loads(value)
    assert envelope == {
        "protocol_version": "1.0",
        "message_type": "pairing.bootstrap",
        "correlation_id": "9a352221-6fbd-4dd0-9fee-d14a07998d72",
        "payload": {
            "control_host": "192.168.100.72:8765",
            "media_host": "192.168.100.72:8766",
            "pairing_code": "12345678",
            "certificate_sha256": "A" * 64,
            "expires_at_unix": 1_792_931_082,
        },
    }

    output = tmp_path / "pairing.png"
    write_pairing_qr(output, value)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert not (tmp_path / "pairing.png.tmp").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("control_host", "https://attacker.invalid"),
        ("media_host", "192.168.1.2:0"),
        ("pairing_code", "1234567"),
        ("certificate_sha256", "a" * 64),
        ("expires_at_unix", 0),
    ],
)
def test_pairing_bootstrap_rejects_invalid_fields(field: str, value: object) -> None:
    arguments: dict[str, object] = {
        "control_host": "192.168.100.72:8765",
        "media_host": "192.168.100.72:8766",
        "pairing_code": "12345678",
        "certificate_sha256": "A" * 64,
        "expires_at_unix": 1_792_931_082,
    }
    arguments[field] = value

    with pytest.raises(ValueError):
        build_pairing_bootstrap(**arguments)  # type: ignore[arg-type]
