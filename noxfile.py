import nox

nox.options.sessions = ["format", "test", "type_check"]

supported_python_versions = ["3.7", "3.8", "3.9", "3.10"]


coverage_hook_script = """\
from pathlib import Path
import sysconfig

(Path(sysconfig.get_path("purelib")) / "coverage.pth").write_text(
    "import coverage; coverage.process_startup()",
    encoding="utf-8",
)
"""


@nox.session(name="format", reuse_venv=True)
def format_(session: nox.Session):
    session.install("black", "isort")
    options = ["--check"] if session.posargs == ["--check"] else []
    for command in ["isort", "black"]:
        session.run(command, *options, "src", "tests", "noxfile.py")


@nox.session(python=supported_python_versions)
def test(session: nox.Session):
    session.install(".[test]")
    session.run("python", "-c", coverage_hook_script)
    session.run(
        "coverage", "run", "-m", "pytest", "-v", env={"COVERAGE_PROCESS_START": "pyproject.toml"}
    )
    session.run("coverage", "combine")
    session.run("coverage", "report", "--show-missing", "--fail-under", "100")


@nox.session(python=supported_python_versions)
def type_check(session: nox.Session):
    session.install(".")
    session.run("npx", "pyright", external=True)


@nox.session
def build(session: nox.Session):
    session.install("build", "flit-core")
    session.run("python", "-m", "build", "-n")
