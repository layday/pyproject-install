from __future__ import annotations

import os
from pathlib import Path
import sys
import sysconfig
import venv

import pytest

from pyproject_install import _core as core


def test_generate_paths_outside_venv(
    base_interpreter: str,
):
    base_paths = sysconfig.get_paths(
        vars={"base": sys.base_prefix, "platbase": sys.base_exec_prefix}
    )
    runtime_metadata = core.extract_python_runtime_metadata(base_interpreter, sys.base_prefix)
    paths = core.generate_wheel_scheme(
        runtime_metadata,
        "foo-0.0.0-py3-none-any.whl",
        True,
    )
    assert paths.keys() == {"purelib", "platlib", "scripts", "data", "headers"}
    assert all(paths[s] == base_paths[s] for s in {"purelib", "platlib", "scripts", "data"})
    assert paths["headers"] == os.path.join(base_paths["include"], "foo")


def test_generate_paths_inside_venv(
    tmp_path: Path,
):
    venv.create(tmp_path)
    interpreter = os.path.join(
        tmp_path,
        "Scripts" if sys.platform == "win32" else "bin",
        "python",
    )
    runtime_metadata = core.extract_python_runtime_metadata(interpreter, None)
    paths = core.generate_wheel_scheme(
        runtime_metadata,
        "foo-0.0.0-py3.none.any.whl",
        True,
    )
    assert paths.keys() == {"purelib", "platlib", "scripts", "data"}
    assert all(os.path.commonpath([p, tmp_path]) == str(tmp_path) for p in paths.values())


def test_cannot_use_custom_prefix_with_apple_framework_build(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sys.base_prefix", sys.prefix)
    monkeypatch.setattr("sysconfig.get_scheme_names", lambda: ("osx_framework_library",))
    with pytest.raises(ValueError, match="Cannot override Apple framework prefix"):
        exec(core.runtime_metadata_script.format({}))
