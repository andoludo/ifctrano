import nox
from nox import Session

nox.options.reuse_existing_virtualenvs = True


@nox.session(python=["3.12"])
def install(session: Session) -> None:
    groups = ["main", "dev", "docs"]
    session.run(
        "poetry",
        "install",
        "--no-root",
        "--sync",
        f"--only={','.join(groups)}",
        external=True,
    )


@nox.session(python=["3.12"])
def linting(session: Session) -> None:
    session.run("poetry", "run", "black", ".")
    session.run("poetry", "run", "mypy")
    session.run(
        "poetry",
        "run",
        "ruff",
        "check",
        "--fix",
        "--show-fixes",
        "--exit-non-zero-on-fix",
    )


@nox.session(python=["3.12"])
def tests(session: Session) -> None:
    session.run("poetry", "run", "pytest", "-m", "not large and not simulate")


@nox.session(python=["3.12"])
def simulation(session: Session) -> None:
    session.run("poetry", "run", "pytest", "-m", "simulate")


@nox.session(python=["3.12"])
def integration(session: Session) -> None:
    session.run("poetry", "run", "pytest", "-m", "integration")
