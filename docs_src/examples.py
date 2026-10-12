"""Simulated examples of the documentation.

    python -m docs_src.examples [NAME ...]
    python -m docs_src.examples --list

Each example translates IFC models with ifctrano, simulates them with trano in the
OpenModelica container (Docker must be running) and writes, in ``docs/tutorials/figures``:

- ``<name>.html``: the interactive figure included in the tutorial page,
- ``<name>.md``: the table of key numbers shown under the figure.

These files are generated, never edited, and not committed: the documentation pipeline runs
every example before building the pages, so the published results are those of the current
code. Signals are looked up on the data bus of trano, which carries the same names for every
library.
"""

import argparse
import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
from numpy.typing import NDArray
import plotly.graph_objects as go  # type: ignore[import-untyped]
import yaml
from buildingspy.io.outputfile import Reader  # type: ignore[import-untyped]
from plotly.subplots import make_subplots  # type: ignore[import-untyped]
from trano.data_models.conversion import convert_network  # type: ignore[import-untyped]
from trano.elements.library.library import Library  # type: ignore[import-untyped]
from trano.simulate.simulate import (  # type: ignore[import-untyped]
    MODELICA_ENVIRONMENT,
    SimulationOptions,
    client,
    container,
    simulate,
)
from trano.utils.utils import is_success  # type: ignore[import-untyped]

from ifctrano.base import Libraries, Vector
from ifctrano.building import Building
from ifctrano.hvac import HeatingOptions, ProductionKind
from tests.hvac import example_hom_heating

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[1]
FIGURES = ROOT / "docs" / "tutorials" / "figures"
MODELS = ROOT / "tests" / "models" / "space_boundary"
HOUR, DAY, KELVIN = 3600.0, 86400.0, 273.15
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
"""Categorical slots in fixed order (validated reference palette, light and dark)."""
NEUTRAL, MUTED = "#8a8985", "#b8b7b1"
"""Ink of the reference lines and of the axes, readable on light and dark pages."""
MAX_ZONE_LINES = len(SERIES)
"""Above this number of zones, the zones are drawn as a band (minimum to maximum) and their mean."""

ZONE_TEMPERATURE = r"\.dataBus\.TZon(\w+)$"
OUTDOOR_TEMPERATURE = (r"weaBus\.TDryBul$", r"\.sim\.Te$")
RADIATOR_HEAT = r"\.radiator_\w+\.Q_flow$"
"""Heat input into the water of the radiators [W]: negative when they heat the room (Buildings)."""
ENERGY_COUNTERS = {
    "Heat from the generator [kWh]": r"\.dataBus\.heat_energy\w+$",
    "Gas [kWh]": r"\.dataBus\.fuel_energy\w+$",
    "Electricity [kWh]": r"\.dataBus\.electric_energy\w+$",
}


class SimulationError(RuntimeError):
    """OpenModelica could not check or simulate a model."""


@dataclass(frozen=True)
class Period:
    """Simulated days of the year; the first ``warm_up`` days are left out of the key numbers."""

    start: int
    days: int
    warm_up: int = 2

    @property
    def start_time(self) -> float:
        return self.start * DAY

    @property
    def end_time(self) -> float:
        return (self.start + self.days) * DAY

    @property
    def evaluated_from(self) -> float:
        return (self.start + self.warm_up) * DAY


WINTER = Period(start=0, days=10)
"""The first ten days of January in Uccle, the default weather of trano."""
SPRING = Period(start=80, days=10)
"""Ten sunny-enough days from 21 March, when the orientation of the windows matters most."""


@dataclass(frozen=True)
class Case:
    """An IFC model translated with given options and simulated with a given library."""

    label: str
    ifc: str
    library: Libraries = "Buildings"
    heating: bool = False
    """Add the federated heating model of ExampleHOM (``tests/hvac/example_hom_heating.py``)."""
    heat_generator: ProductionKind | None = None
    north_axis: tuple[float, float] = (0.0, 1.0)
    configure: Callable[[dict[str, Any]], None] | None = None
    """Edits the configuration before trano builds the model, as a user would edit the YAML."""

    def building(self, directory: Path) -> Building:
        hvac = (
            [example_hom_heating.write(directory / "ExampleHOM_heating.ifc")]
            if self.heating
            else None
        )
        return Building.from_ifc(
            MODELS / self.ifc,
            hvac_file_paths=hvac,
            heating_options=HeatingOptions(heat_generator=self.heat_generator),
        )

    def configuration(self, directory: Path) -> dict[str, Any]:
        north_axis = Vector(x=self.north_axis[0], y=self.north_axis[1], z=0)
        configuration = self.building(directory).to_config(north_axis=north_axis)
        if self.configure is not None:
            self.configure(configuration)
        return configuration


@dataclass(frozen=True)
class Example:
    """A figure of the documentation and the simulations it shows."""

    name: str
    title: str
    cases: tuple[Case, ...]
    period: Period = WINTER
    zone: str | None = None
    """Zone compared between the cases; the mean of the zones when absent."""
    set_points: dict[str, float] = field(default_factory=dict)
    """Reference lines of the temperature panel [degC], by label."""


@dataclass(frozen=True)
class Series:
    time: NDArray[np.float64]  # [s]
    data: NDArray[np.float64]


class Result:
    """Signals of a trano result file, looked up by pattern."""

    def __init__(self, mat: Path) -> None:
        self.reader = Reader(str(mat), "dymola")
        self.names: list[str] = self.reader.varNames()

    def find(self, pattern: str) -> list[str]:
        return sorted(name for name in self.names if re.search(pattern, name))

    def hourly(self, name: str, scale: float = 1.0, offset: float = 0.0) -> Series:
        """Hourly means of a signal, which preserve the energy of a power."""
        time, values = self.reader.values(name)
        grid = np.arange(time[0], time[-1], HOUR / 10)
        fine = np.interp(grid, time, values) * scale + offset
        hours = len(grid) // 10
        return Series(
            time=grid[: hours * 10 : 10] + HOUR / 2,
            data=fine[: hours * 10].reshape(hours, 10).mean(axis=1),
        )

    def zones(self) -> dict[str, Series]:
        """Air temperature of each zone [degC], by zone name."""
        zones: dict[str, Series] = {}
        for name in self.find(ZONE_TEMPERATURE):
            zone = re.search(ZONE_TEMPERATURE, name).group(1).lower()  # type: ignore[union-attr]
            zones.setdefault(zone, self.hourly(name, offset=-KELVIN))
        return dict(sorted(zones.items()))

    def outdoor(self) -> Series | None:
        names = next(
            (names for pattern in OUTDOOR_TEMPERATURE if (names := self.find(pattern))),
            [],
        )
        return self.hourly(names[0], offset=-KELVIN) if names else None

    def heat(self) -> Series | None:
        """Heat delivered by the radiators [kW]."""
        names = self.find(RADIATOR_HEAT)
        if not names:
            return None
        series = [self.hourly(name, scale=-1e-3) for name in names]
        return Series(
            time=series[0].time, data=np.sum([s.data for s in series], axis=0)
        )

    def energy(self, pattern: str, since: float) -> float | None:
        """Increase of the energy counters matching ``pattern`` after ``since`` [kWh].

        The data bus appears under every component wired to it: each counter is counted once.
        """
        counters = {
            name.rsplit(".", 1)[-1]: name for name in reversed(self.find(pattern))
        }
        if not counters:
            return None
        total = 0.0
        for name in counters.values():
            time, values = self.reader.values(name)
            total += float(values[-1] - np.interp(since, time, values))
        return total


def zone_label(zone: str) -> str:
    """Readable zone name: ``space_kitchen5_dsw`` becomes ``Kitchen5``."""
    name = re.sub(r"^space_?", "", zone)
    name = re.sub(r"_[a-z0-9]{3}$", "", name)
    return name.replace("_", " ").strip().capitalize() or zone


def _evaluated(series: Series, since: float) -> NDArray[np.float64]:
    return series.data[series.time >= since]


def _mean_zone(result: Result) -> Series:
    zones = list(result.zones().values())
    return Series(
        time=zones[0].time, data=np.mean([zone.data for zone in zones], axis=0)
    )


def _compared_zone(example: Example, result: Result) -> Series:
    if example.zone is None:
        return _mean_zone(result)
    return result.zones()[example.zone]


def run(case: Case, period: Period, directory: Path) -> Result:
    """Translate and simulate a case; the result file lands in ``directory``."""
    name = re.sub(r"\W+", "_", case.label).lower()
    configuration_path = directory / f"{name}.yaml"
    configuration_path.write_text(yaml.safe_dump(case.configuration(directory)))
    network = convert_network(
        name, configuration_path, library=Library.from_configuration(case.library)
    )
    options = SimulationOptions(
        start_time=int(period.start_time),
        end_time=int(period.end_time),
        number_of_intervals=period.days * 24 * 4,
    )
    project = directory / name
    project.mkdir()
    # A network renders its model once: render it here to check it again on failure.
    network.set_weather_path_to_container_path(project)
    model = network.model()
    container_name = f"ifctrano_{name}"
    logger.info("Simulating %s with %s", case.label, case.library)
    output = simulate(
        project, network, options=options, container_name=container_name, model=model
    )
    if not is_success(output, options=options):
        raise SimulationError(
            f"{case.label}: {output.output.decode()[-3000:]}\n--- OpenModelica errors ---\n"
            f"{diagnose(project, network.name, model, container_name)[-6000:]}"
        )
    result_files = sorted(project.rglob("*building_res.mat"))
    if not result_files:
        raise SimulationError(f"{case.label}: no result file in {project}")
    return Result(result_files[0])


def diagnose(project: Path, name: str, model: str, container_name: str) -> str:
    """OpenModelica messages when loading and checking a model that failed to build."""
    (project / "diagnostic.mo").write_text(model)
    (project / "diagnostic.mos").write_text(
        f'loadModel(Modelica, {{"{MODELICA_ENVIRONMENT.modelica_version}"}});\n'
        "getErrorString();\n"
        'loadFile("/simulation/diagnostic.mo");\n'
        "getErrorString();\n"
        f"checkModel({name}.building);\n"
        "getErrorString();\n"
    )
    with container(client(), project, container_name=container_name) as container_:
        output = container_.exec_run(cmd="omc /simulation/diagnostic.mos").output
    return str(output.decode())


def _temperature_traces(
    plot: go.Figure, example: Example, results: Mapping[str, Result]
) -> None:
    if len(results) == 1:
        result = next(iter(results.values()))
        zones = result.zones()
        if len(zones) <= MAX_ZONE_LINES:
            for index, (zone, series) in enumerate(zones.items()):
                _line(plot, series, zone_label(zone), SERIES[index], row=1)
        else:
            _band(plot, list(zones.values()), f"{len(zones)} zones", SERIES[0])
    else:
        for index, (label, result) in enumerate(results.items()):
            _line(plot, _compared_zone(example, result), label, SERIES[index], row=1)
    outdoor = next(iter(results.values())).outdoor()
    if outdoor is not None:
        plot.add_scatter(
            x=outdoor.time / DAY,
            y=outdoor.data,
            name="Outdoor",
            legend="legend",
            line={"color": NEUTRAL, "width": 1.5, "dash": "dot"},
            hovertemplate="%{y:.1f} °C",
            row=1,
            col=1,
        )
    for label, value in example.set_points.items():
        plot.add_hline(
            y=value, line={"color": MUTED, "width": 1, "dash": "dash"}, row=1, col=1
        )
        plot.add_annotation(
            x=1.0,
            xref="x domain",
            y=value,
            yref="y",
            text=label,
            showarrow=False,
            xanchor="right",
            yanchor="bottom",
            font={"size": 10, "color": NEUTRAL},
        )


def _line(plot: go.Figure, series: Series, label: str, color: str, row: int) -> None:
    """A line in the temperature panel (row 1, °C) or in the heat panel (row 2, kW)."""
    unit = "°C" if row == 1 else "kW"
    plot.add_scatter(
        x=series.time / DAY,
        y=series.data,
        name=label,
        legend="legend" if row == 1 else "legend2",
        line={"color": color, "width": 2},
        hovertemplate=f"%{{y:.1f}} {unit}",
        row=row,
        col=1,
    )


def _band(plot: go.Figure, zones: Sequence[Series], label: str, color: str) -> None:
    values = np.array([zone.data for zone in zones])
    days = zones[0].time / DAY
    plot.add_scatter(
        x=days,
        y=values.max(axis=0),
        line={"width": 0},
        showlegend=False,
        hoverinfo="skip",
        row=1,
        col=1,
    )
    plot.add_scatter(
        x=days,
        y=values.min(axis=0),
        fill="tonexty",
        fillcolor="rgba(42,120,214,0.18)",
        line={"width": 0},
        name=f"{label}, minimum to maximum",
        legend="legend",
        hoverinfo="skip",
        row=1,
        col=1,
    )
    plot.add_scatter(
        x=days,
        y=values.mean(axis=0),
        name=f"{label}, mean",
        legend="legend",
        line={"color": color, "width": 2},
        hovertemplate="%{y:.1f} °C",
        row=1,
        col=1,
    )


def figure(example: Example, results: Mapping[str, Result]) -> go.Figure:
    """Zone and outdoor temperatures, and the heat of the radiators when there are some."""
    heats = {
        label: heat
        for label, result in results.items()
        if (heat := result.heat()) is not None
    }
    rows = 2 if heats else 1
    plot = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=["Air temperature [°C]", "Heat of the radiators [kW]"][:rows],
    )
    _temperature_traces(plot, example, results)
    for index, (label, heat) in enumerate(heats.items()):
        _line(
            plot,
            heat,
            label if len(heats) > 1 else "Radiators",
            SERIES[index],
            row=2,
        )
    plot.update_xaxes(title_text="Day of the year", row=rows, col=1)
    return _layout(plot, example.title, 330 * rows)


def _layout(plot: go.Figure, title: str, height: int) -> go.Figure:
    plot.update_layout(
        title={"text": title, "x": 0.0, "xanchor": "left", "font": {"size": 15}},
        height=height,
        margin={"l": 60, "r": 200, "t": 80, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "family": "Roboto, Helvetica, Arial, sans-serif",
            "size": 12,
            "color": NEUTRAL,
        },
        hovermode="x unified",
    )
    for index, axis in enumerate(
        sorted(key for key in plot.layout if key.startswith("yaxis"))
    ):
        top = plot.layout[axis].domain[1] if plot.layout[axis].domain else 1.0
        plot.layout["legend" if index == 0 else f"legend{index + 1}"] = {
            "x": 1.02,
            "xanchor": "left",
            "y": top,
            "yanchor": "top",
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11},
            "tracegroupgap": 2,
        }
    plot.update_xaxes(showgrid=False, linecolor=MUTED, ticks="outside", tickcolor=MUTED)
    plot.update_yaxes(
        gridcolor="rgba(138,137,133,0.25)", zeroline=False, linecolor=MUTED
    )
    return plot


def key_numbers(
    example: Example, results: Mapping[str, Result]
) -> list[dict[str, str]]:
    """Rows of the table under the figure, over the evaluated days.

    One row per zone for a single case, one row per case (the compared zone) otherwise; the
    energy columns are on the row of the whole building.
    """
    since = example.period.evaluated_from
    if len(results) == 1:
        label, result = next(iter(results.items()))
        rows = [
            _temperature_row(label, zone_label(zone), series, since)
            for zone, series in result.zones().items()
        ]
        if len(rows) > 1:
            rows.append(
                _temperature_row(label, "Mean of the zones", _mean_zone(result), since)
            )
        rows[-1] |= _energy_columns(result, since)
        return rows
    zone = zone_label(example.zone) if example.zone else "Mean of the zones"
    return [
        _temperature_row(label, zone, _compared_zone(example, result), since)
        | _energy_columns(result, since)
        for label, result in results.items()
    ]


def _temperature_row(
    case: str, zone: str, series: Series, since: float
) -> dict[str, str]:
    values = _evaluated(series, since)
    return {
        "Case": case,
        "Zone": zone,
        "Mean [°C]": f"{values.mean():.1f}",
        "Minimum [°C]": f"{values.min():.1f}",
        "Maximum [°C]": f"{values.max():.1f}",
    }


def _energy_columns(result: Result, since: float) -> dict[str, str]:
    """Heat of the radiators and the energy counters of the data bus, for the whole building."""
    columns = {}
    heat = result.heat()
    if heat is not None:
        columns["Radiator heat [kWh]"] = f"{_evaluated(heat, since).sum():.0f}"
        columns["Peak radiator heat [kW]"] = f"{_evaluated(heat, since).max():.1f}"
    for column, pattern in ENERGY_COUNTERS.items():
        energy = result.energy(pattern, since)
        if energy is not None:
            columns[column] = f"{energy:.0f}"
    return columns


def table(rows: Sequence[dict[str, str]]) -> str:
    """Markdown table; cells missing from a row are left empty."""
    columns = list(dict.fromkeys(column for row in rows for column in row))
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    lines += [
        "| " + " | ".join(row.get(column, "") for column in columns) + " |"
        for row in rows
    ]
    return "\n".join(lines) + "\n"


def outputs(example: Example) -> tuple[Path, Path]:
    """The figure and the table of an example, included in the tutorial pages."""
    return FIGURES / f"{example.name}.html", FIGURES / f"{example.name}.md"


def write(example: Example, results: Mapping[str, Result]) -> None:
    """Write the figure and the table of key numbers of a simulated example."""
    figure_path, table_path = outputs(example)
    FIGURES.mkdir(parents=True, exist_ok=True)
    html = figure(example, results).to_html(
        include_plotlyjs="cdn",
        full_html=False,
        config={"displaylogo": False, "responsive": True},
        div_id=example.name,
    )
    figure_path.write_text(html)
    period = example.period
    caption = (
        f"Days {period.start + period.warm_up + 1} to {period.start + period.days} of the year "
        f"(the first {period.warm_up} simulated days are a warm-up and are left out).\n\n"
    )
    table_path.write_text(caption + table(key_numbers(example, results)))


def missing_outputs() -> list[str]:
    """Outputs of the examples that are not generated: the pages would build without them."""
    return [
        str(path.relative_to(ROOT))
        for example in EXAMPLES
        for path in outputs(example)
        if not path.exists()
    ]


def constant_set_point(configuration: dict[str, Any]) -> None:
    """Heat to the occupied set point day and night: the setback temperature is the set point."""
    for space in configuration["spaces"]:
        for emission in space.get("emissions", []):
            control = (
                emission.get("valve", {}).get("control", {}).get("emission_control")
            )
            if control is not None:
                control["parameters"] = {"temperature_heating_setback": 294.15}


DEFAULT_SET_POINTS = {"Set point 21 °C": 21.0, "Setback 15.85 °C": 15.85}
EXAMPLES = (
    Example(
        name="two_zones",
        title="Two zones without heating, Buildings",
        cases=(Case(label="Two zones", ifc="TwoZones.ifc"),),
    ),
    Example(
        name="libraries",
        title="Two zones simulated with four libraries, mean air temperature of the zones",
        cases=(
            Case(label="Buildings", ifc="TwoZones.ifc", library="Buildings"),
            Case(label="IDEAS", ifc="TwoZones.ifc", library="IDEAS"),
            Case(
                label="AixLib reduced order",
                ifc="TwoZones.ifc",
                library="reduced_order",
            ),
            Case(label="ISO 13790", ifc="TwoZones.ifc", library="iso_13790"),
        ),
    ),
    Example(
        name="many_zones",
        title="Multizone building without heating, Buildings",
        cases=(Case(label="Multizone", ifc="MultiZoneBuilding.ifc"),),
    ),
    Example(
        name="realistic",
        title="Duplex apartment without heating, Buildings",
        cases=(Case(label="Duplex", ifc="Duplex_A.ifc"),),
    ),
    Example(
        name="heating",
        title="ExampleHOM with its hydronic heating, Buildings",
        cases=(Case(label="Gas boiler", ifc="ExampleHOM.ifc", heating=True),),
        set_points=DEFAULT_SET_POINTS,
    ),
    Example(
        name="orientation",
        title="ExampleHOM kitchen without heating, as built and turned by 180°",
        cases=(
            Case(
                label="As built (kitchen windows south and west)", ifc="ExampleHOM.ifc"
            ),
            Case(
                label="Turned by 180° (north and east)",
                ifc="ExampleHOM.ifc",
                north_axis=(0.0, -1.0),
            ),
        ),
        period=SPRING,
        zone="space_kitchen5_dsw",
    ),
    Example(
        name="heat_generators",
        title="ExampleHOM heated by a gas boiler and by an air-to-water heat pump, mean of the zones",
        cases=(
            Case(label="Gas boiler", ifc="ExampleHOM.ifc", heating=True),
            Case(
                label="Air-to-water heat pump",
                ifc="ExampleHOM.ifc",
                heating=True,
                heat_generator=ProductionKind.air_water_heat_pump,
            ),
        ),
        set_points=DEFAULT_SET_POINTS,
    ),
    Example(
        name="control",
        title="ExampleHOM living room with a night setback and with a constant set point",
        cases=(
            Case(label="Night setback (default)", ifc="ExampleHOM.ifc", heating=True),
            Case(
                label="Constant set point",
                ifc="ExampleHOM.ifc",
                heating=True,
                configure=constant_set_point,
            ),
        ),
        zone="space_living1_v3g",
        set_points=DEFAULT_SET_POINTS,
    ),
)


def run_example(example: Example) -> None:
    with TemporaryDirectory() as directory:
        results = {
            case.label: run(case, example.period, Path(directory))
            for case in example.cases
        }
        write(example, results)


def main(arguments: Sequence[str] | None = None) -> None:
    names = [example.name for example in EXAMPLES]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "examples",
        nargs="*",
        metavar="NAME",
        help=f"examples to run, all by default: {names}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when a figure or table of the examples is missing, then exit",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the names of the examples as JSON and exit",
    )
    parsed = parser.parse_args(arguments)
    if parsed.list:
        print(json.dumps(names))
        return
    if parsed.check:
        if missing := missing_outputs():
            parser.exit(1, f"Missing outputs of the examples: {missing}\n")
        return
    selected = parsed.examples or names
    if unknown := set(selected) - set(names):
        parser.error(f"unknown examples {sorted(unknown)}, choose among {names}")
    logging.basicConfig(level=logging.INFO)
    for example in EXAMPLES:
        if example.name in selected:
            run_example(example)


if __name__ == "__main__":
    main()
