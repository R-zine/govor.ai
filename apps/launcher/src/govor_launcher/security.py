from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


@dataclass(frozen=True)
class TlsIdentity:
    certificate: Path
    private_key: Path
    fingerprint_sha256: str


def ensure_tls_identity(security_root: Path) -> TlsIdentity:
    security_root.mkdir(parents=True, exist_ok=True)
    certificate_path = security_root / "gateway-certificate.pem"
    private_key_path = security_root / "gateway-private-key.pem"
    if certificate_path.exists() != private_key_path.exists():
        raise RuntimeError("the gateway TLS identity is incomplete; restore it from backup")
    if not certificate_path.exists():
        _generate_identity(certificate_path, private_key_path)
        _protect_private_directory(security_root)
    certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
    _ = serialization.load_pem_private_key(private_key_path.read_bytes(), password=None)
    if certificate.not_valid_after_utc <= dt.datetime.now(dt.UTC) + dt.timedelta(days=30):
        raise RuntimeError("the gateway certificate expires in less than 30 days")
    fingerprint = certificate.fingerprint(hashes.SHA256()).hex().upper()
    return TlsIdentity(certificate_path, private_key_path, fingerprint)


def _generate_identity(certificate_path: Path, private_key_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=3072)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "govor.ai")])
    now = dt.datetime.now(dt.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("govor.ai"),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.IPAddress(ipaddress.ip_address("::1")),
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )
    private_key_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(private_key_path, stat.S_IRUSR | stat.S_IWUSR)
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))


def _protect_private_directory(path: Path) -> None:
    if os.name != "nt":
        os.chmod(path, stat.S_IRWXU)
        return
    whoami = Path(os.environ["SYSTEMROOT"]) / "System32" / "whoami.exe"
    identity = subprocess.run(  # noqa: S603 - fixed Windows system tool
        [str(whoami)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    username = identity.stdout.strip()
    if identity.returncode != 0 or not username:
        raise RuntimeError("Windows user identity is unavailable; TLS key ACL was not applied")
    icacls = Path(os.environ["SYSTEMROOT"]) / "System32" / "icacls.exe"
    result = subprocess.run(  # noqa: S603 - fixed Windows system tool and argument array
        [
            str(icacls),
            str(path),
            "/inheritance:r",
            "/grant:r",
            f"{username}:(OI)(CI)F",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("failed to restrict the gateway TLS/key directory ACL")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
