from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
import pprint
import shutil
import subprocess
import sys
import textwrap
from typing import Any, BinaryIO

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile
from installer.utils import parse_metadata_file, parse_wheel_filename

from . import __version__

COMMON_SCHEME_NAMES = frozenset({"purelib", "platlib", "scripts", "data"})
DISPARATE_SCHEME_NAMES = frozenset({"include", "platinclude"})

LOGGING_ENABLED = False


def log(message: str, always: bool = False):
    if always or LOGGING_ENABLED:
        print(message, file=sys.stderr)


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

if hasattr(sysconfig, "get_default_scheme"):
    scheme = sysconfig.get_default_scheme()
else:
    scheme = sysconfig._get_default_scheme()

print(
    json.dumps(
        {
            "prefix": sys.prefix,
            "in_venv": in_venv,
            "scheme": scheme,
            "paths": sysconfig.get_paths(),
            "launcher_kind": launcher_kind,
        },
    )
)
"""


class Skip(str):
    def __repr__(self):
        return f"<Skip: {self}>"


SKIP_VENV_HEADERS = Skip("There is no standard location for headers in a venv")


def extract_python_runtime_metadata(interpreter: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output([interpreter, "-Ic", runtime_metadata_script]))


def generate_wheel_scheme(
    runtime_metadata: Mapping[str, Any],
    prefix: str | None,
    wheel_filename: str,
    wheel_is_pure: bool,
):
    base_paths: Mapping[str, str] = runtime_metadata["paths"]

    scheme = {d: p for d, p in base_paths.items() if d in COMMON_SCHEME_NAMES}
    if prefix is not None:
        scheme = {
            d: os.path.join(prefix, os.path.relpath(p, runtime_metadata["prefix"]))
            for d, p in scheme.items()
        }

    if runtime_metadata["in_venv"]:
        scheme["headers"] = SKIP_VENV_HEADERS
    else:
        include_path = base_paths["include" if wheel_is_pure else "platinclude"]
        if prefix is not None:
            include_path = os.path.join(
                prefix, os.path.relpath(include_path, runtime_metadata["prefix"])
            )
        distribution = parse_wheel_filename(wheel_filename).distribution
        scheme["headers"] = os.path.join(include_path, distribution)

    return scheme


def is_wheel_pure(wheel_file: WheelFile):
    stream = wheel_file.read_dist_info("WHEEL")
    metadata = parse_metadata_file(stream)
    return metadata["Root-Is-Purelib"] == "true"


def validate_runtime_metadata(runtime_metadata: Mapping[str, Any], custom_prefix: bool):
    if not runtime_metadata["launcher_kind"]:
        raise ValueError("Could not determine launcher kind")
    if not custom_prefix and not runtime_metadata["in_venv"]:
        raise ValueError("Attempted installation at base prefix.  Pass `--prefix` to override")
    if custom_prefix:
        unoverridable_paths = [
            p
            for d, p in runtime_metadata["paths"].items()
            if d
            in COMMON_SCHEME_NAMES
            | (frozenset() if runtime_metadata["in_venv"] else DISPARATE_SCHEME_NAMES)
            and os.path.commonpath([runtime_metadata["prefix"], p]) != runtime_metadata["prefix"]
        ]
        if unoverridable_paths:
            raise ValueError("Scheme contains unoverridable paths", unoverridable_paths)


class CustomSchemeDictionaryDestination(SchemeDictionaryDestination):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._skip_schemes = frozenset(
            s for s, v in self.scheme_dict.items() if isinstance(v, Skip)
        )

    def write_file(self, scheme: str, path: str | os.PathLike[str], stream: BinaryIO):
        if scheme in self._skip_schemes:
            log(f"Skipping {scheme} file: '{path}'", True)
        else:
            log(f"Writing {scheme} file: '{path}'")
            super().write_file(scheme, path, stream)

    def write_script(self, name: str, module: str, attr: str, section: str):  # pragma: no cover
        log(f"Writing script: '{name}'")
        super().write_script(name, module, attr, section)


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(description="Python wheel installer for the masses")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="increase verbosity",
    )
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

    if args.verbose:
        global LOGGING_ENABLED
        LOGGING_ENABLED = True

    runtime_metadata = extract_python_runtime_metadata(args.interpreter)

    log("Runtime metadata:")
    log(textwrap.indent(pprint.pformat(runtime_metadata), "  "))
    log("")

    validate_runtime_metadata(runtime_metadata, args.prefix is not None)

    with WheelFile.open(args.wheel) as wheel:
        scheme = generate_wheel_scheme(
            runtime_metadata,
            args.prefix,
            args.wheel,
            is_wheel_pure(wheel),
        )

        log("Scheme:")
        log(textwrap.indent(pprint.pformat(scheme), "  "))
        log("")

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
