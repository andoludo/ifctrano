"""Models generated from IFC simulate in every library.

The other tests check the translation; these run the generated models in OpenModelica, over one
day only: long enough to show that the model builds, initialises and integrates, short enough
for every push. Needs Docker (trano simulates in the OpenModelica image); run with
``pytest -m simulate``.
"""

from pathlib import Path
from typing import get_args

import numpy as np
import pytest

from docs_src.examples import Case, Period, run
from ifctrano.base import Libraries

ONE_DAY = Period(start=0, days=1, warm_up=0)
"""1 January in Uccle, the default weather of trano."""
TWO_ZONES = ("space_01_dup", "space_01_uj9")
PLAUSIBLE_TEMPERATURES = (-10.0, 35.0)
"""Bounds of the zone air temperature [degC] of an unheated house starting at 21 degC in winter."""


@pytest.mark.simulate
@pytest.mark.parametrize("library", get_args(Libraries))
def test_two_zones_simulate(library: Libraries, tmp_path: Path) -> None:
    result = run(
        Case(label=f"two_zones_{library}", ifc="TwoZones.ifc", library=library),
        ONE_DAY,
        tmp_path,
    )

    zones = result.zones()
    assert tuple(zones) == TWO_ZONES
    lowest, highest = PLAUSIBLE_TEMPERATURES
    for zone, series in zones.items():
        assert len(series.data) == 24, zone
        assert np.isfinite(series.data).all(), zone
        assert lowest < series.data.min(), (zone, series.data.min())
        assert series.data.max() < highest, (zone, series.data.max())
    outdoor = result.outdoor()
    assert outdoor is not None
    # Free-floating zones lose heat to the colder outdoor air.
    assert outdoor.data.mean() < min(series.data.mean() for series in zones.values())
