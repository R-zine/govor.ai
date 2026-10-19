from __future__ import annotations

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from govor_launcher.security import ensure_tls_identity


def test_tls_identity_is_stable_and_private_key_matches(tmp_path) -> None:
    first = ensure_tls_identity(tmp_path / "security")
    second = ensure_tls_identity(tmp_path / "security")

    certificate = x509.load_pem_x509_certificate(first.certificate.read_bytes())
    private_key = serialization.load_pem_private_key(first.private_key.read_bytes(), None)
    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert certificate.public_key().public_numbers() == private_key.public_key().public_numbers()
    assert "localhost" in certificate.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value.get_values_for_type(x509.DNSName)
