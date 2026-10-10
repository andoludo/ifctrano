"""Simulation of the heating model generated from IFC.

Needs Docker (trano simulates with the OpenModelica image); run with
``pytest -m simulate``.
"""

import re
from pathlib import Path

import numpy as np
import pytest
from buildingspy.io.outputfile import Reader  # type: ignore
from trano.simulate.simulate import (  # type: ignore
    MODELICA_ENVIRONMENT,
    SimulationOptions,
    client,
    container,
    simulate,
)
from trano.topology import Network  # type: ignore
from trano.utils.utils import is_success  # type: ignore

from ifctrano.building import Building
from tests.conftest import SPACE_BOUNDARY_IFC
from tests.hvac import example_hom_heating

ONE_DAY = 24 * 3600
KELVIN = 273.15


def _series(reader: Reader, pattern: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Time series of the result variables whose name matches ``pattern``."""
    names = [name for name in reader.varNames() if re.search(pattern, name)]
    return {name: reader.values(name) for name in names}


def _diagnose(network: Network, project: Path) -> str:
    """OpenModelica messages when loading and checking the generated model."""
    (project / "diagnostic.mo").write_text(network.model())
    (project / "diagnostic.mos").write_text(
        f'loadModel(Modelica, {{"{MODELICA_ENVIRONMENT.modelica_version}"}});\n'
        "getErrorString();\n"
        'loadFile("/simulation/diagnostic.mo");\n'
        "getErrorString();\n"
        f"checkModel({network.name}.building);\n"
        "getErrorString();\n"
        "getAvailableLibraryVersions(Buildings);\n"
    )
    with container(client(), project) as container_:
        return str(
            container_.exec_run(cmd="omc /simulation/diagnostic.mos").output.decode()
        )


def _last_day(time: np.ndarray, values: np.ndarray, end: float) -> np.ndarray:
    return values[time >= end - ONE_DAY]  # type: ignore[no-any-return]


@pytest.mark.simulate
def test_simulate_heating_model(tmp_path: Path) -> None:
    heating = example_hom_heating.write(tmp_path / "ExampleHOM_heating.ifc")
    building = Building.from_ifc(
        SPACE_BOUNDARY_IFC / "ExampleHOM.ifc", hvac_file_paths=[heating]
    )
    heated = [
        space["id"] for space in building.to_config()["spaces"] if "emissions" in space
    ]
    network = building.create_network(library="Buildings")
    project = tmp_path / "simulation"
    project.mkdir()
    options = SimulationOptions(end_time=2 * ONE_DAY)

    results = simulate(project, network, options=options)

    if not is_success(results, options=options):
        pytest.fail(
            f"{results.output.decode()[-3000:]}\n--- diagnostic ---\n"
            f"{_diagnose(network, project)[-8000:]}"
        )
    result_files = list(project.rglob("*building_res.mat"))
    assert result_files, f"No result file in {list(project.rglob('*'))}"
    reader = Reader(str(result_files[0]), "openmodelica")
    end = float(options.end_time)

    # Heated rooms stay comfortable on the second (winter) day.
    for space_id in heated:
        temperatures = _series(reader, rf"\b{space_id}\.air\.vol\.T$")
        assert temperatures, f"No air temperature for {space_id}"
        (time, values), *_ = temperatures.values()
        last_day = _last_day(time, values, end) - KELVIN
        assert last_day.mean() > 17.0, (space_id, last_day.mean())
        assert last_day.max() < 30.0, (space_id, last_day.max())

    # The radiators deliver heat.
    flows = _series(reader, r"radiator_space_[a-z0-9_]+\.Q_flow$")
    assert flows, [n for n in reader.varNames() if "radiator" in n][:50]
    delivered = sum(
        _last_day(time, values, end).mean() for time, values in flows.values()
    )
    assert delivered > 0
