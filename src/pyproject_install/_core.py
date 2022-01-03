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
from installer.utils import SCHEME_NAMES, parse_metadata_file, parse_wheel_filename

from . import __version__

runtime_metadata_script = """\
import json
import os
import sys
import sysconfig


in_venv = sys.prefix != sys.base_prefix

launcher_kind = None
if os.name != "nt":
    launcher_kind = "posix"
if "amd64" in sys.version.lower():
    launcher_kind = "win-amd64"
if "(arm64)" in sys.version.lower():
    launcher_kind = "win-arm64"
if "(arm)" in sys.version.lower():
    launcher_kind = "win-arm"
if sys.platform == "win32":
    launcher_kind = "win-ia32"

path_prefixes = {}
if path_prefixes is not None:
    paths = sysconfig.get_paths(vars=path_prefixes)
else:
    paths = sysconfig.get_paths()

print(
    json.dumps(
        {{
            "in_venv": in_venv,
            "paths": paths,
            "launcher_kind": launcher_kind,
        }},
    )
)
"""


class Skip(str):
    pass


SKIP = Skip()


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
    if runtime_metadata["in_venv"]:
        scheme["headers"] = SKIP
    else:
        distribution = parse_wheel_filename(wheel_filename).distribution
        scheme["headers"] = os.path.join(
            runtime_metadata["paths"]["include" if wheel_is_pure else "platinclude"], distribution
        )
    return scheme


def is_wheel_pure(wheel_file: WheelFile):
    stream = wheel_file.read_dist_info("WHEEL")
    metadata = parse_metadata_file(stream)
    return metadata["Root-Is-Purelib"] == "true"


def validate_runtime_metadata(runtime_metadata: Mapping[str, Any], prefix: str | None):
    if prefix is None and not runtime_metadata["in_venv"]:
        raise ValueError("Attempted installation at base prefix.  Pass `--prefix` to override")
    if prefix is not None:
        unoverridable_paths = [
            p
            for d, p in runtime_metadata["paths"].items()
            if d in SCHEME_NAMES and os.path.commonpath([prefix, p]) != prefix
        ]
        if unoverridable_paths:
            raise ValueError("Scheme contains unoverridable paths", unoverridable_paths)
    if not runtime_metadata["launcher_kind"]:
        raise ValueError("Could not extract launcher kind")


class CustomSchemeDictionaryDestination(SchemeDictionaryDestination):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._skip_schemes = frozenset(s for s, v in self.scheme_dict.items() if v is SKIP)

    def write_file(self, scheme: str, path: str | os.PathLike[str], stream: BinaryIO):
        if scheme in self._skip_schemes:
            print(f"Skipping {scheme} file: '{path}'", file=sys.stderr)
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
    validate_runtime_metadata(runtime_metadata, args.prefix)

    with WheelFile.open(args.wheel) as wheel:
        scheme = generate_wheel_scheme(
            runtime_metadata,
            args.wheel,
            is_wheel_pure(wheel),
        )
        destination = CustomSchemeDictionaryDestination(
            scheme,
            interpreter=args.interpreter,
            script_kind=runtime_metadata["launcher_kind"],
        )
        install(
            wheel,
            destination,
            {
                "INSTALLER": b"pyproject-install",
            },
        )
