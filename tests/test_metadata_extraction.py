from __future__ import annotations

import os
from pathlib import Path
import sys
import venv

from pyproject_install import _core as core


def test_generate_paths_outside_venv(
    base_paths: dict[str, str],
    base_interpreter: str,
):
    runtime_metadata = core.extract_python_runtime_metadata(base_interpreter)
    paths = core.generate_wheel_scheme(
        runtime_metadata,
        "foo-0.0.0-py3-none-any.whl",
        True,
        sys.base_prefix,
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
    runtime_metadata = core.extract_python_runtime_metadata(interpreter)
    paths = core.generate_wheel_scheme(
        runtime_metadata,
        "foo-0.0.0-py3.none.any.whl",
        True,
        None,
    )
    assert paths.keys() == {"purelib", "platlib", "scripts", "data"}
    assert all(os.path.commonpath([p, tmp_path]) == str(tmp_path) for p in paths.values())