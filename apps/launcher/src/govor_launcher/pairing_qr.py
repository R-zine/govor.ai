from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

import segno

_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
_FINGERPRINT_PATTERN = re.compile(r"^[0-9A-F]{64}$")
_PAIRING_CODE_PATTERN = re.compile(r"^[0-9]{8}$")


def build_pairing_bootstrap(
    *,
    control_host: str,
    media_host: str,
    pairing_code: str,
    certificate_sha256: str,
    expires_at_unix: int,
    correlation_id: UUID | None = None,
) -> str:
    _validate_host_port(control_host)
    _validate_host_port(media_host)
    if not _PAIRING_CODE_PATTERN.fullmatch(pairing_code):
        raise ValueError("pairing code must contain exactly eight digits")
    if not _FINGERPRINT_PATTERN.fullmatch(certificate_sha256):
        raise ValueError("certificate fingerprint must contain 64 uppercase hexadecimal digits")
    if expires_at_unix < 1 or expires_at_unix > 4_102_444_800:
        raise ValueError("pairing expiry is outside the supported range")
    envelope = {
        "protocol_version": "1.0",
        "message_type": "pairing.bootstrap",
        "correlation_id": str(correlation_id or uuid4()),
        "payload": {
            "control_host": control_host,
            "media_host": media_host,
            "pairing_code": pairing_code,
            "certificate_sha256": certificate_sha256,
            "expires_at_unix": expires_at_unix,
        },
    }
    return json.dumps(envelope, ensure_ascii=True, separators=(",", ":"))


def write_pairing_qr(path: Path, bootstrap: str) -> None:
    if len(bootstrap.encode("utf-8")) > 2_048:
        raise ValueError("pairing bootstrap exceeds the QR payload limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        code = segno.make_qr(bootstrap, error="m", boost_error=False)
        code.save(str(temporary), kind="png", scale=8, border=4, dark="#111827", light="#FFFFFF")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_pairing_bootstrap(path: Path, bootstrap: str) -> None:
    encoded = bootstrap.encode("utf-8")
    if len(encoded) > 2_048:
        raise ValueError("pairing bootstrap exceeds the file payload limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_host_port(value: str) -> None:
    host, separator, raw_port = value.rpartition(":")
    if separator != ":" or not _HOST_PATTERN.fullmatch(host) or not raw_port.isascii():
        raise ValueError("gateway address must be a bounded host:port value")
    if not raw_port.isdigit() or not 1 <= int(raw_port) <= 65_535:
        raise ValueError("gateway port must be between 1 and 65535")
