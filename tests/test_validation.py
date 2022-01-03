import os
import sys

import pytest

from pyproject_install import _core as core


def test_cannot_use_custom_prefix_with_apple_framework_build():
    prefix = os.path.realpath("/foo")
    metadata = core.extract_python_runtime_metadata(sys.executable, prefix)
    metadata["paths"]["headers"] = os.path.realpath("/bar")
    with pytest.raises(ValueError, match="unoverridable paths"):
        core.validate_runtime_metadata(metadata, prefix)


def test_launcher_kind_cannot_be_none():
    metadata = core.extract_python_runtime_metadata(sys.executable, None)
    metadata["launcher_kind"] = None
    with pytest.raises(ValueError, match="launcher kind"):
        core.validate_runtime_metadata(metadata, None)
