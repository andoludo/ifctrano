import nox
from nox import Session

# Every session delegates to uv, which manages the project environment from uv.lock.
nox.options.default_venv_backend = "none"


@nox.session
def install(session: Session) -> None:
    session.run("uv", "sync", "--locked", "--all-groups", external=True)


@nox.session
def linting(session: Session) -> None:
    session.run("uv", "run", "--locked", "black", ".", external=True)
    session.run("uv", "run", "--locked", "mypy", external=True)
    session.run(
        "uv",
        "run",
        "--locked",
        "ruff",
        "check",
        "--fix",
        "--show-fixes",
        "--exit-non-zero-on-fix",
        external=True,
    )


@nox.session
def tests(session: Session) -> None:
    session.run(
        "uv",
        "run",
        "--locked",
        "pytest",
        "-m",
        "not large and not simulate",
        external=True,
    )


@nox.session
def simulation(session: Session) -> None:
    session.run("uv", "run", "--locked", "pytest", "-m", "simulate", external=True)


@nox.session
def integration(session: Session) -> None:
    session.run("uv", "run", "--locked", "pytest", "-m", "integration", external=True)
