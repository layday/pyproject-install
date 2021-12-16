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
from functools import partial
import json
import sys
import sysconfig

get_paths = sysconfig.get_paths
path_vars = {}
if path_vars is not None:
    # Apple framework builds don't use a common prefix
    if "osx_framework_library" in sysconfig.get_scheme_names():
        get_paths = partial(get_paths, scheme="posix_prefix")
    get_paths = partial(get_paths, vars=path_vars)

print(
    json.dumps(
        {{
            "prefix": sys.prefix,
            "in_venv": sys.prefix != sys.base_prefix,
            "paths": get_paths(),
        }}
    )
)
"""


def extract_python_runtime_metadata(
    interpreter: str,
    custom_prefix: str | None,
) -> dict[str, Any]:
    script = runtime_metadata_script.format(
        {
            "installed_base": custom_prefix,
            "base": custom_prefix,
            "installed_platbase": custom_prefix,
            "platbase": custom_prefix,
        }
        if custom_prefix is not None
        else None
    )
    return json.loads(subprocess.check_output([interpreter, "-Ic", script]))


def generate_wheel_scheme(
    runtime_metadata: Mapping[str, Any],
    wheel_filename: str,
    wheel_is_pure: bool,
):
    scheme: dict[str, str] = {
        d: p for d, p in runtime_metadata["paths"].items() if d in SCHEME_NAMES
    }
    if not runtime_metadata["in_venv"]:
        distribution = parse_wheel_filename(wheel_filename).distribution
        scheme["headers"] = os.path.join(
            runtime_metadata["paths"]["include" if wheel_is_pure else "platinclude"], distribution
        )
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

    runtime_metadata = extract_python_runtime_metadata(args.interpreter, args.prefix)
    if not runtime_metadata["in_venv"] and args.prefix is None:
        raise ValueError(
            "Attempted installation at base prefix; aborting.  Pass `--prefix` to override"
        )

    with WheelFile.open(args.wheel) as wheel:
        scheme = generate_wheel_scheme(
            runtime_metadata,
            args.wheel,
            is_wheel_pure(wheel),
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
