import nox
from nox import Session

nox.options.reuse_existing_virtualenvs = True


@nox.session(python=["3.11"])
def install(session: Session) -> None:
    session.run(
        "uv",
        "sync",
        "--all-groups",
        external=True,
    )


@nox.session(python=["3.11"])
def linting(session: Session) -> None:
    session.run("uv", "run", "black", ".", external=True)
    session.run("uv", "run", "mypy", external=True)
    session.run(
        "uv",
        "run",
        "ruff",
        "check",
        "--fix",
        "--show-fixes",
        "--exit-non-zero-on-fix",
        external=True,
    )


@nox.session(python=["3.11"])
def tests(session: Session) -> None:
    session.run("uv", "run", "pytest", "-m", "not large", external=True)


@nox.session(python=["3.11"])
def integration(session: Session) -> None:
    session.run("uv", "run", "pytest", "-m", "integration", external=True)
