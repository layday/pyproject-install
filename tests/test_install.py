from __future__ import annotations

import os
from pathlib import Path
import sys
import venv
from zipfile import ZipFile

import pytest

from pyproject_install import _core as core


@pytest.fixture
def fake_wheel(
    tmp_path: Path,
):
    wheel_path = os.path.join(tmp_path, "foo-0.0.0-py3-none-any.whl")
    with ZipFile(wheel_path, "w") as wheel_zip:
        wheel_zip.writestr(
            "foo-0.0.0.dist-info/METADATA",
            """\
Metadata-Version: 2.1
Name: foo
Version: 1.0.0
""",
        )
        wheel_zip.writestr(
            "foo-0.0.0.dist-info/RECORD",
            """\
foo-0.0.0.dist-info/METADATA,,
foo-0.0.0.dist-info/RECORD,,
foo-0.0.0.dist-info/WHEEL,,
""",
        )
        wheel_zip.writestr(
            "foo-0.0.0.dist-info/WHEEL",
            """\
Wheel-Version: 1.0
Generator: pyproject-install
Root-Is-Purelib: true
Tag: py3-none-any
""",
        )
    return wheel_path


@pytest.fixture
def fake_wheel_with_header_file(
    tmp_path: Path,
):
    wheel_path = os.path.join(tmp_path, "foo-0.0.0-py3-none-any.whl")
    with ZipFile(wheel_path, "w") as wheel_zip:
        wheel_zip.writestr(
            "foo-0.0.0.dist-info/METADATA",
            """\
Metadata-Version: 2.1
Name: foo
Version: 1.0.0
""",
        )
        wheel_zip.writestr(
            "foo-0.0.0.dist-info/RECORD",
            """\
foo-0.0.0.data/headers/foo.h,,
foo-0.0.0.dist-info/METADATA,,
foo-0.0.0.dist-info/RECORD,,
foo-0.0.0.dist-info/WHEEL,,
""",
        )
        wheel_zip.writestr(
            "foo-0.0.0.dist-info/WHEEL",
            """\
Wheel-Version: 1.0
Generator: pyproject-install
Root-Is-Purelib: true
Tag: py3-none-any
""",
        )
        wheel_zip.writestr(
            "foo-0.0.0.data/headers/foo.h",
            b"",
        )
    return wheel_path


def test_basic_install(
    tmp_path: Path,
    fake_wheel: str,
):
    core.main(
        [
            "--prefix",
            str(tmp_path),
            fake_wheel,
        ]
    )


def test_combined_prefix_and_interpreter_install_in_venv(
    tmp_path: Path,
    base_interpreter: str,
    fake_wheel: str,
):
    core.main(
        [
            "--interpreter",
            base_interpreter,
            "--prefix",
            str(tmp_path),
            fake_wheel,
        ]
    )


def test_cannot_install_in_base_prefix_implicitly(
    base_interpreter: str,
    fake_wheel: str,
):
    with pytest.raises(ValueError, match="Attempted installation at base prefix"):
        core.main(
            [
                "--interpreter",
                base_interpreter,
                fake_wheel,
            ]
        )


def test_header_file_skipped_reported(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    fake_wheel_with_header_file: str,
):
    venv_path = tmp_path.joinpath("venv")
    venv.create(venv_path)
    interpreter = os.path.join(
        venv_path,
        "Scripts" if sys.platform == "win32" else "bin",
        "python",
    )
    core.main(
        [
            "--interpreter",
            interpreter,
            "--prefix",
            str(tmp_path.joinpath("prefix")),
            fake_wheel_with_header_file,
        ]
    )
    assert capsys.readouterr().err == "Skipping headers file: 'foo.h'\n"
