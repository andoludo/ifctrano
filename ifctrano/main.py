import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, get_args

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from ifctrano.base import Libraries
from ifctrano.building import Building
from ifctrano.exceptions import InvalidLibraryError

app = typer.Typer()
CHECKMARK = "[green]✔[/green]"
CROSS_MARK = "[red]✘[/red]"


@app.command()
def create(
    model: Annotated[
        str,
        typer.Argument(help="Local path to the ifc file."),
    ],
    library: Annotated[
        str,
        typer.Argument(help="Modelica library to be used for simulation."),
    ] = "Buildings",
) -> None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        if library not in get_args(Libraries):
            raise InvalidLibraryError(
                f"Invalid library {library}. Valid libraries are {get_args(Libraries)}"
            )
        modelica_model_path = Path(model).resolve().with_suffix(".mo")
        task = progress.add_task(
            description=f"Generating model {modelica_model_path.name} with library {library} from {model}",
            total=None,
        )
        building = Building.from_ifc(Path(model))
        modelica_model = building.create_model()
        progress.update(task, completed=True)
        task = progress.add_task(description="Writing model to file...", total=None)
        modelica_model_path.write_text(modelica_model)
        progress.remove_task(task)
        print(f"{CHECKMARK} Model generated at {modelica_model_path}")


@app.command()
def verify() -> None:
    verification_ifc = Path(__file__).parent / "example" / "verification.ifc"
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress, TemporaryDirectory() as temp_dir:
        temp_ifc_file = Path(temp_dir) / verification_ifc.name
        shutil.copy(verification_ifc, temp_ifc_file)
        task = progress.add_task(
            description="Trying to create a model from a test file...",
            total=None,
        )
        building = Building.from_ifc(temp_ifc_file)
        building.save_model()
        if temp_ifc_file.parent.joinpath(f"{building.name}.mo").exists():
            progress.remove_task(task)
            print(f"{CHECKMARK} Model successfully created... your system is ready.")
        else:
            progress.remove_task(task)
            print(
                f"{CROSS_MARK} Model could not be created... please check your system."
            )
