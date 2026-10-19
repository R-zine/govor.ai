from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

_PBKDF2_ITERATIONS = 200_000
_MAX_DEVICES = 8
_MAX_FAILURES_PER_WINDOW = 5
_FAILURE_WINDOW_SECONDS = 60.0


class PairingRejected(ValueError):
    """A deliberately generic pairing or authentication rejection."""


class PairingAuthority:
    """A small file-backed credential authority shared by host and media processes.

    The file contains only salted hashes. The one-time pairing code and issued device
    credential are returned to the launcher/client respectively and are never persisted.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path)
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def create_pairing_code(self, *, ttl_seconds: int = 600) -> tuple[str, int]:
        if ttl_seconds not in range(60, 3601):
            raise ValueError("pairing-code lifetime must be between 60 and 3600 seconds")
        code = f"{secrets.randbelow(100_000_000):08d}"
        salt = secrets.token_bytes(16)
        expires_at = int(self._clock()) + ttl_seconds
        with self._lock:
            state = self._read()
            state["pairing"] = {
                "salt": salt.hex(),
                "digest": _derive(code, salt),
                "expires_at": expires_at,
            }
            self._write(state)
        return code, expires_at

    def exchange_code(
        self,
        *,
        code: str,
        device_id: str,
        device_name: str,
        client_id: str,
    ) -> str:
        now = self._clock()
        self._check_rate_limit(client_id, now)
        try:
            normalized_device_id = str(UUID(device_id))
        except ValueError as error:
            self._record_failure(client_id, now)
            raise PairingRejected("pairing was rejected") from error
        normalized_name = device_name.strip()
        if not 1 <= len(normalized_name) <= 64 or len(code) != 8 or not code.isdigit():
            self._record_failure(client_id, now)
            raise PairingRejected("pairing was rejected")

        with self._lock:
            state = self._read()
            pairing = state.get("pairing")
            if not isinstance(pairing, dict) or int(pairing.get("expires_at", 0)) < int(now):
                self._record_failure(client_id, now)
                raise PairingRejected("pairing was rejected")
            salt = bytes.fromhex(str(pairing.get("salt", "")))
            expected = str(pairing.get("digest", ""))
            if not hmac.compare_digest(_derive(code, salt), expected):
                self._record_failure(client_id, now)
                raise PairingRejected("pairing was rejected")

            credential = secrets.token_urlsafe(32)
            credential_salt = secrets.token_bytes(16)
            devices = state.setdefault("devices", {})
            if not isinstance(devices, dict):
                devices = {}
                state["devices"] = devices
            if normalized_device_id not in devices and len(devices) >= _MAX_DEVICES:
                raise PairingRejected("pairing was rejected")
            devices[normalized_device_id] = {
                "name": normalized_name,
                "salt": credential_salt.hex(),
                "digest": _derive(credential, credential_salt),
                "created_at": int(now),
            }
            state["pairing"] = None
            self._write(state)
            self._failures.pop(client_id, None)
            return credential

    def authenticate(self, *, device_id: str, credential: str) -> bool:
        if not 32 <= len(credential) <= 256:
            return False
        try:
            normalized_device_id = str(UUID(device_id))
        except ValueError:
            return False
        with self._lock:
            state = self._read()
        devices = state.get("devices", {})
        if not isinstance(devices, dict):
            return False
        record = devices.get(normalized_device_id)
        if not isinstance(record, dict):
            return False
        try:
            salt = bytes.fromhex(str(record["salt"]))
            expected = str(record["digest"])
        except (KeyError, ValueError):
            return False
        return hmac.compare_digest(_derive(credential, salt), expected)

    def device_count(self) -> int:
        with self._lock:
            devices = self._read().get("devices", {})
        return len(devices) if isinstance(devices, dict) else 0

    def _check_rate_limit(self, client_id: str, now: float) -> None:
        failures = self._failures[client_id]
        while failures and now - failures[0] > _FAILURE_WINDOW_SECONDS:
            failures.popleft()
        if len(failures) >= _MAX_FAILURES_PER_WINDOW:
            raise PairingRejected("pairing was rejected")

    def _record_failure(self, client_id: str, now: float) -> None:
        self._failures[client_id].append(now)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "pairing": None, "devices": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("gateway credential store is unreadable") from error
        if not isinstance(value, dict) or value.get("version") != 1:
            raise RuntimeError("gateway credential store has an unsupported format")
        return value

    def _write(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(8)}.tmp")
        data = json.dumps(state, indent=2, sort_keys=True) + "\n"
        try:
            temporary.write_text(data, encoding="utf-8")
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


def _derive(secret: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    ).hex()
