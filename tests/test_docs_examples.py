"""The parts of the documentation examples that do not need a simulation."""

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
import pytest

from docs_src.examples import (
    DAY,
    EXAMPLES,
    HOUR,
    Case,
    Example,
    Period,
    Result,
    Series,
    constant_set_point,
    figure,
    key_numbers,
    main,
    outputs,
    table,
    zone_label,
)

PERIOD = Period(start=0, days=4, warm_up=1)


class StubResult(Result):
    """Result with given hourly signals instead of a result file."""

    def __init__(self, zones: dict[str, float], heat: float | None = None) -> None:
        self.time = (np.arange(PERIOD.days * 24) * HOUR + HOUR / 2).astype(np.float64)
        self._zones = zones
        self._heat = heat

    def zones(self) -> dict[str, Series]:
        return {
            zone: Series(self.time, np.full(self.time.shape, value))
            for zone, value in self._zones.items()
        }

    def outdoor(self) -> Series:
        return Series(self.time, np.sin(self.time / DAY))

    def heat(self) -> Series | None:
        if self._heat is None:
            return None
        return Series(self.time, np.full(self.time.shape, self._heat))

    def energy(self, pattern: str, since: float) -> float | None:
        return None


def _example(cases: int, zone: str | None = None) -> Example:
    return Example(
        name="stub",
        title="Stub",
        cases=tuple(
            Case(label=f"Case {index}", ifc="TwoZones.ifc") for index in range(cases)
        ),
        period=PERIOD,
        zone=zone,
    )


def test_zone_label() -> None:
    assert zone_label("space_kitchen5_dsw") == "Kitchen5"
    assert zone_label("space_01_uj9") == "01"


def test_key_numbers_of_one_case() -> None:
    rows = key_numbers(
        _example(1),
        {"Case 0": StubResult({"space_a_abc": 20.0, "space_b_abc": 22.0}, heat=2.0)},
    )
    assert [row["Zone"] for row in rows] == ["A", "B", "Mean of the zones"]
    assert rows[-1]["Mean [°C]"] == "21.0"
    # Three evaluated days of 2 kW.
    assert rows[-1]["Radiator heat [kWh]"] == "144"
    assert "Radiator heat [kWh]" not in rows[0]


def test_key_numbers_compare_a_zone_between_cases() -> None:
    results = {
        "Case 0": StubResult({"space_a_abc": 20.0, "space_b_abc": 22.0}),
        "Case 1": StubResult({"space_a_abc": 18.0, "space_b_abc": 22.0}),
    }
    rows = key_numbers(_example(2, zone="space_a_abc"), results)
    assert [(row["Case"], row["Zone"], row["Mean [°C]"]) for row in rows] == [
        ("Case 0", "A", "20.0"),
        ("Case 1", "A", "18.0"),
    ]


def test_table_leaves_missing_cells_empty() -> None:
    assert (
        table([{"a": "1"}, {"a": "2", "b": "3"}])
        == "| a | b |\n|---|---|\n| 1 |  |\n| 2 | 3 |\n"
    )


@pytest.mark.parametrize(("zones", "traces"), [(2, 2), (6, 3)])
def test_many_zones_are_drawn_as_a_band(zones: int, traces: int) -> None:
    result = StubResult({f"space_{index}_abc": 20.0 + index for index in range(zones)})
    plot = figure(_example(1), {"Case 0": result})
    temperature_traces = [trace for trace in plot.data if trace.name != "Outdoor"]
    assert len(temperature_traces) == traces


def test_radiator_heat_has_its_own_panel() -> None:
    plot = figure(_example(1), {"Case 0": StubResult({"space_a_abc": 20.0}, heat=1.0)})
    assert {trace.yaxis for trace in plot.data} == {"y", "y2"}


def test_constant_set_point() -> None:
    control: dict[str, Any] = {"emission_control": {"id": "emission_control_space_a"}}
    configuration = {
        "spaces": [
            {
                "id": "space_a",
                "emissions": [{"radiator": {}}, {"valve": {"control": control}}],
            }
        ]
    }
    constant_set_point(configuration)
    assert control["emission_control"]["parameters"] == {
        "temperature_heating_setback": 294.15
    }


def test_examples_use_existing_models() -> None:
    models = Path(__file__).parent / "models" / "space_boundary"
    assert all(
        (models / case.ifc).exists() for example in EXAMPLES for case in example.cases
    )
    assert len({example.name for example in EXAMPLES}) == len(EXAMPLES)


def test_unknown_example_is_rejected() -> None:
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_list_prints_the_example_names(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--list"])
    assert json.loads(capsys.readouterr().out) == [example.name for example in EXAMPLES]


def test_check_fails_on_missing_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("docs_src.examples.FIGURES", tmp_path)
    monkeypatch.setattr("docs_src.examples.ROOT", tmp_path)
    with pytest.raises(SystemExit) as error:
        main(["--check"])
    assert error.value.code == 1
    for example in EXAMPLES:
        for path in outputs(example):
            path.write_text("")
    main(["--check"])


class CounterReader:
    """Reader of a result where the data bus counter of a boiler appears under two components."""

    def values(self, name: str) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        return np.array([0.0, DAY, 2 * DAY]), np.array([0.0, 10.0, 30.0])


def test_energy_counts_each_counter_of_the_data_bus_once() -> None:
    result = Result.__new__(Result)
    result.reader = CounterReader()
    result.names = [
        "building.bus1.dataBus.heat_energyBoiler_1",
        "building.production1.dataBus.heat_energyBoiler_1",
    ]
    assert result.energy(r"\.dataBus\.heat_energy\w+$", since=DAY) == 20.0
