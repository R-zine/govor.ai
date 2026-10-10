from __future__ import annotations

import os
from typing import Literal, cast

from .app import create_media_app

_token = os.environ.get("GOVOR_DEV_PAIRING_TOKEN", "")
_source = os.environ.get("GOVOR_MEDIA_SOURCE", "diagnostic").lower()
app = create_media_app(
    pairing_token=_token,
    media_source=cast(Literal["diagnostic", "renderer"], _source),
)
