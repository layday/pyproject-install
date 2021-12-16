from __future__ import annotations

import os
import sys
import sysconfig

import pytest


@pytest.fixture
def base_paths():
    return sysconfig.get_paths(
        vars={
            "base": sys.base_prefix,
            "platbase": sys.base_exec_prefix,
        }
    )


@pytest.fixture
def base_interpreter(base_paths):
    if sys.platform == "win32":
        return os.path.join(sys.base_prefix, "python")
    else:
        return os.path.join(base_paths["scripts"], "python")
