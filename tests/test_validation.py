import os
import sys

import pytest

from pyproject_install import _core as core


def test_simple_validation_passes():
    metadata = core.extract_python_runtime_metadata(sys.executable)
    core.validate_runtime_metadata(metadata, False)


def test_cannot_use_custom_prefix_with_unoverridable_paths():
    metadata = core.extract_python_runtime_metadata(sys.executable)
    metadata["paths"]["purelib"] = os.path.realpath("/bar")
    with pytest.raises(ValueError, match="unoverridable paths"):
        core.validate_runtime_metadata(metadata, True)


def test_launcher_kind_cannot_be_none():
    metadata = core.extract_python_runtime_metadata(sys.executable)
    metadata["launcher_kind"] = None
    with pytest.raises(ValueError, match="launcher kind"):
        core.validate_runtime_metadata(metadata, False)


def test_cannot_install_at_base_prefix_implicitly():
    metadata = core.extract_python_runtime_metadata(sys.executable)
    metadata["in_venv"] = False
    with pytest.raises(ValueError, match="installation at base prefix"):
        core.validate_runtime_metadata(metadata, False)
