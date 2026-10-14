from __future__ import annotations

import io

import pytest
from govor_provider_interfaces import ProviderAuthenticationError
from govor_provider_router import InMemoryCredentialStore, credential_cli
from govor_provider_router.secrets import validate_credential_target


def test_in_memory_store_validates_and_manages_values() -> None:
    store = InMemoryCredentialStore()

    store.set_secret("valid-target", "secret")
    assert store.get_secret("valid-target") == "secret"
    assert store.delete_secret("valid-target")
    assert not store.delete_secret("valid-target")
    with pytest.raises(ProviderAuthenticationError):
        store.get_secret("valid-target")
    with pytest.raises(ValueError, match="identifier"):
        validate_credential_target("INVALID TARGET")
    with pytest.raises(ValueError, match="non-empty"):
        store.set_secret("valid-target", "")
    with pytest.raises(ValueError, match="2560"):
        store.set_secret("valid-target", "x" * 2_561)


def test_credential_cli_set_status_and_delete_without_displaying_value(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = InMemoryCredentialStore()
    monkeypatch.setattr(credential_cli, "WindowsCredentialStore", lambda: store)
    monkeypatch.setattr(credential_cli.sys, "stdin", io.StringIO("CLI-SECRET\n"))

    assert credential_cli.main(["set", "test-target"]) == 0
    assert credential_cli.main(["status", "test-target"]) == 0
    assert credential_cli.main(["delete", "test-target"]) == 0
    assert credential_cli.main(["delete", "test-target"]) == 0

    output = capsys.readouterr().out
    assert "CLI-SECRET" not in output
    assert "was not displayed" in output
    assert "was not present" in output


def test_credential_cli_reports_missing_status_without_secret_detail(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(credential_cli, "WindowsCredentialStore", InMemoryCredentialStore)

    assert credential_cli.main(["status", "missing-target"]) == 1

    assert capsys.readouterr().out.strip() == (
        "Credential unavailable: ProviderAuthenticationError"
    )


def test_credential_cli_rejects_an_empty_standard_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(credential_cli, "WindowsCredentialStore", InMemoryCredentialStore)
    monkeypatch.setattr(credential_cli.sys, "stdin", io.StringIO("\n"))

    with pytest.raises(SystemExit):
        credential_cli.main(["set", "test-target"])
