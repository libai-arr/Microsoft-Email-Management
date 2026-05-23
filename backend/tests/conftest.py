import base64
import os

import pytest


@pytest.fixture
def encryption_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()
