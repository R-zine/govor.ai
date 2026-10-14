"""Credential storage boundary; provider secrets never enter application settings."""

from __future__ import annotations

import re
from typing import Protocol

from govor_provider_interfaces import ProviderAuthenticationError

_TARGET_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")


class CredentialStore(Protocol):
    def get_secret(self, target: str) -> str: ...

    def set_secret(self, target: str, secret: str) -> None: ...

    def delete_secret(self, target: str) -> bool: ...


def validate_credential_target(target: str) -> str:
    if not _TARGET_PATTERN.fullmatch(target):
        raise ValueError("credential target must be a bounded lowercase identifier")
    return target


class InMemoryCredentialStore:
    """Test-only store; never use it for production credentials."""

    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values = dict(values or {})

    def get_secret(self, target: str) -> str:
        validate_credential_target(target)
        try:
            return self._values[target]
        except KeyError as error:
            raise ProviderAuthenticationError("provider credential is not configured") from error

    def set_secret(self, target: str, secret: str) -> None:
        validate_credential_target(target)
        _validate_secret(secret)
        self._values[target] = secret

    def delete_secret(self, target: str) -> bool:
        validate_credential_target(target)
        return self._values.pop(target, None) is not None


def _validate_secret(secret: str) -> None:
    if not secret or len(secret.encode("utf-8")) > 2_560:
        raise ValueError("credential must be non-empty and at most 2560 bytes")
