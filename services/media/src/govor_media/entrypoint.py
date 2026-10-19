from __future__ import annotations

import os
from typing import Literal, cast

from .app import create_media_app

_token = os.environ.get("GOVOR_DEV_PAIRING_TOKEN", "")
_credential_file = os.environ.get("GOVOR_GATEWAY_CREDENTIALS_FILE")
_secure_gateway = os.environ.get("GOVOR_SECURE_GATEWAY", "false").lower() == "true"
_source = os.environ.get("GOVOR_MEDIA_SOURCE", "diagnostic").lower()
_ice_fixture_host = os.environ.get("GOVOR_MEDIA_ICE_FIXTURE_ADVERTISE_HOST")
_ice_fixture_port_text = os.environ.get("GOVOR_MEDIA_ICE_FIXTURE_BIND_PORT")
_ice_fixture_port = int(_ice_fixture_port_text) if _ice_fixture_port_text else None
app = create_media_app(
    pairing_token=_token or None,
    gateway_credentials_file=_credential_file,
    secure_gateway=_secure_gateway,
    media_source=cast(Literal["diagnostic", "renderer"], _source),
    ice_fixture_advertise_host=_ice_fixture_host,
    ice_fixture_bind_port=_ice_fixture_port,
)
