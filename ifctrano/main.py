from pathlib import Path
from typing import Annotated

import typer
from pydantic import validate_call
from rich.progress import Progress, SpinnerColumn, TextColumn

from ifctrano.base import Libraries
from ifctrano.building import Building

app = typer.Typer()
CHECKMARK = "[green]✔[/green]"
CROSS_MARK = "[red]✘[/red]"


@app.command()
@validate_call
def create(
    model: Annotated[
        str,
        typer.Argument(help="Local path to the ifc file."),
    ],
    library: Annotated[
        Libraries,
        typer.Argument(help="Modelica library to be used for simulation."),
    ] = "Buildings",
) -> None:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
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
