from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
import shutil
import subprocess
import sys
from typing import Any, BinaryIO

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile
from installer.utils import (
    SCHEME_NAMES,
    get_launcher_kind,
    parse_metadata_file,
    parse_wheel_filename,
)

from . import __version__

runtime_metadata_script = """\
import json
import sys
import sysconfig

print(
    json.dumps(
        {
            "prefix": sys.prefix,
            "in_venv": sys.prefix != sys.base_prefix,
            "paths": sysconfig.get_paths(),
        }
    )
)
"""


def extract_python_runtime_metadata(interpreter: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output([interpreter, "-Ic", runtime_metadata_script]))


def generate_wheel_scheme(
    runtime_metadata: Mapping[str, Any],
    wheel_filename: str,
    wheel_is_pure: bool,
    custom_prefix: str | None,
):
    scheme: dict[str, str] = {
        d: p for d, p in runtime_metadata["paths"].items() if d in SCHEME_NAMES
    }
    if not runtime_metadata["in_venv"]:
        distribution = parse_wheel_filename(wheel_filename).distribution
        scheme["headers"] = os.path.join(
            runtime_metadata["paths"]["include" if wheel_is_pure else "platinclude"], distribution
        )
    if custom_prefix is not None and custom_prefix != runtime_metadata["prefix"]:
        scheme = {
            d: os.path.join(custom_prefix, os.path.relpath(p, runtime_metadata["prefix"]))
            for d, p in scheme.items()
        }
    return scheme


def is_wheel_pure(wheel_file: WheelFile):
    stream = wheel_file.read_dist_info("WHEEL")
    metadata = parse_metadata_file(stream)
    return metadata["Root-Is-Purelib"] == "true"


class CustomSchemeDictionaryDestination(SchemeDictionaryDestination):
    def __init__(self, *args: Any, in_venv: bool, **kwargs: Any):
        self._in_venv = in_venv
        super().__init__(*args, **kwargs)

    def write_file(self, scheme: str, path: str | os.PathLike[str], stream: BinaryIO):
        if self._in_venv and scheme == "headers":
            print(f"Skipping header file '{path}'", file=sys.stderr)
        else:
            super().write_file(scheme, path, stream)


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(description="Python wheel installer for the masses")
    parser.add_argument(
        "--version",
        action="version",
        version=f"pyproject-install {__version__}",
    )
    parser.add_argument(
        "--interpreter",
        default=shutil.which("python"),
        help="path of Python interpreter; defaults to `which python`",
    )
    parser.add_argument(
        "--prefix",
        help="custom installation prefix",
    )
    parser.add_argument(
        "wheel",
        help="wheel file to install",
    )

    args = parser.parse_args(argv)

    with WheelFile.open(args.wheel) as wheel:
        runtime_metadata = extract_python_runtime_metadata(args.interpreter)
        if not runtime_metadata["in_venv"] and args.prefix is None:
            raise ValueError(
                "Attempted installation at base prefix; aborting.  Pass `--prefix` to override"
            )

        scheme = generate_wheel_scheme(
            runtime_metadata,
            args.wheel,
            is_wheel_pure(wheel),
            args.prefix,
        )
        destination = CustomSchemeDictionaryDestination(
            scheme,
            in_venv=runtime_metadata["in_venv"],
            interpreter=args.interpreter,
            script_kind=get_launcher_kind(),
        )
        install(
            wheel,
            destination,
            {
                "INSTALLER": b"pyproject-install",
            },
        )
