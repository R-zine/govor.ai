"""Manage provider credentials in the current user's Windows Credential Manager."""

from __future__ import annotations

import argparse
import sys

from .secrets import validate_credential_target
from .windows_credentials import WindowsCredentialStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("set", "status", "delete"))
    parser.add_argument("target", type=validate_credential_target)
    arguments = parser.parse_args(argv)
    store = WindowsCredentialStore()
    if arguments.action == "set":
        secret = sys.stdin.readline().rstrip("\r\n")
        if not secret:
            parser.error("set requires a credential on standard input")
        store.set_secret(arguments.target, secret)
        print(f"Stored credential target '{arguments.target}' in Windows Credential Manager.")
        return 0
    if arguments.action == "delete":
        removed = store.delete_secret(arguments.target)
        print("Credential deleted." if removed else "Credential was not present.")
        return 0
    try:
        store.get_secret(arguments.target)
    except Exception as error:  # noqa: BLE001 - status intentionally maps safe typed errors
        print(f"Credential unavailable: {type(error).__name__}")
        return 1
    print("Credential is configured; its value was not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
