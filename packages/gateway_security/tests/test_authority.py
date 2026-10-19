from __future__ import annotations

import json
from uuid import uuid4

import pytest
from govor_gateway_security import PairingAuthority, PairingRejected


def test_pairing_code_is_one_time_and_store_contains_only_hashes(tmp_path) -> None:
    store = tmp_path / "gateway.json"
    authority = PairingAuthority(store, clock=lambda: 1_000.0)
    code, expires_at = authority.create_pairing_code(ttl_seconds=600)
    device_id = str(uuid4())

    credential = authority.exchange_code(
        code=code,
        device_id=device_id,
        device_name="Learner phone",
        client_id="192.0.2.1",
    )

    assert expires_at == 1_600
    assert len(code) == 8
    assert authority.authenticate(device_id=device_id, credential=credential)
    assert not authority.authenticate(device_id=device_id, credential="x" * 32)
    persisted = store.read_text(encoding="utf-8")
    assert code not in persisted
    assert credential not in persisted
    assert json.loads(persisted)["pairing"] is None
    with pytest.raises(PairingRejected, match="pairing was rejected"):
        authority.exchange_code(
            code=code,
            device_id=str(uuid4()),
            device_name="Another phone",
            client_id="192.0.2.2",
        )


def test_expired_and_rate_limited_pairing_is_rejected(tmp_path) -> None:
    now = [2_000.0]
    authority = PairingAuthority(tmp_path / "gateway.json", clock=lambda: now[0])
    code, _ = authority.create_pairing_code(ttl_seconds=60)
    now[0] = 2_061.0
    with pytest.raises(PairingRejected):
        authority.exchange_code(
            code=code,
            device_id=str(uuid4()),
            device_name="Phone",
            client_id="198.51.100.1",
        )

    now[0] = 3_000.0
    authority.create_pairing_code(ttl_seconds=60)
    for _ in range(5):
        with pytest.raises(PairingRejected):
            authority.exchange_code(
                code="00000000",
                device_id=str(uuid4()),
                device_name="Phone",
                client_id="198.51.100.2",
            )
    with pytest.raises(PairingRejected):
        authority.exchange_code(
            code="00000000",
            device_id=str(uuid4()),
            device_name="Phone",
            client_id="198.51.100.2",
        )


def test_device_limit_is_bounded(tmp_path) -> None:
    authority = PairingAuthority(tmp_path / "gateway.json")
    for index in range(8):
        code, _ = authority.create_pairing_code()
        authority.exchange_code(
            code=code,
            device_id=str(uuid4()),
            device_name=f"Phone {index}",
            client_id=f"203.0.113.{index}",
        )
    code, _ = authority.create_pairing_code()
    with pytest.raises(PairingRejected):
        authority.exchange_code(
            code=code,
            device_id=str(uuid4()),
            device_name="Extra phone",
            client_id="203.0.113.99",
        )
    assert authority.device_count() == 8
