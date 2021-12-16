from __future__ import annotations

import os
import sys

import pytest


@pytest.fixture
def base_interpreter():
    if sys.platform == "win32":
        return os.path.join(sys.base_prefix, "python")
    else:
        return os.path.join(sys.base_prefix, "bin", "python")
