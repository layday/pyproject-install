from __future__ import annotations

import os
from pathlib import Path
import sys
import sysconfig
import venv

from installer.utils import SCHEME_NAMES

from pyproject_install import _core as core


def test_generate_paths_outside_venv(
    base_interpreter: str,
):
    base_paths = sysconfig.get_paths(
        vars={"base": sys.base_prefix, "platbase": sys.base_exec_prefix}
    )
    runtime_metadata = core.extract_python_runtime_metadata(base_interpreter)
    paths = core.generate_wheel_scheme(
        runtime_metadata,
        None,
        "foo-0.0.0-py3-none-any.whl",
        True,
    )
    assert paths.keys() == set(SCHEME_NAMES)
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
    runtime_metadata = core.extract_python_runtime_metadata(interpreter)
    paths = core.generate_wheel_scheme(
        runtime_metadata,
        None,
        "foo-0.0.0-py3.none.any.whl",
        True,
    )
    assert paths.keys() == set(SCHEME_NAMES)
    assert all(
        os.path.commonpath([paths[s], tmp_path]) == str(tmp_path)
        for s in {"purelib", "platlib", "scripts", "data"}
    )
    assert paths["headers"] is core.SKIP_VENV_HEADERS
