"""Orientation of the envelope and physics of the generated models.

ifctrano measures orientations as compass bearings (clockwise from north, in
degrees) while trano and the Modelica libraries use the azimuth of the
Buildings library (radians from south, positive towards west). Before trano
0.39, ifctrano wrote the bearing in radians as the azimuth, which turned every
facade by 180 degrees (north facades were simulated facing south).

The snapshots in ``tests/data/physics`` hold the physical parameters of the
generated Buildings models (``tests.physics``). ``before_azimuth_fix.json``
holds them as generated with trano 0.35, before the correction: the tests check
that the only differences are the corrected orientations and the hydronic fixes
of trano 0.39, so that the upgrade changes no other physics.
"""

import math
from pathlib import Path
from typing import Any, Optional

import pytest
from deepdiff import DeepDiff
from trano.elements import Space as TranoSpace, Window  # type: ignore

from ifctrano.base import Vector
from ifctrano.building import Building
from ifctrano.space_boundary import HORIZONTAL_AZIMUTH, bearing_to_azimuth
from tests.conftest import OVERWRITE_RESULTS, SPACE_BOUNDARY_IFC
from tests.hvac import example_hom_heating
from tests.physics import dump, load, physics

PHYSICS_PATH = Path(__file__).parent / "data" / "physics"
NORTH = Vector(x=0, y=1, z=0)
TOLERANCE = 1e-5
SOUTH, WEST, NORTH_AZIMUTH, EAST = 0.0, 1.57, 3.14, -1.57
CASES = {
    "example_hom_heating": "ExampleHOM.ifc",
    "residential_house": "Residential House.ifc",
    "two_zones": "TwoZones.ifc",
    "multizone": "MultiZoneBuilding.ifc",
}
TRANO_0_39_HYDRONIC_FIXES = {
    ("boiler", "dIns"): "tank insulation 0.1 m instead of 2 mm",
    (
        "boiler",
        "nominal_mass_flow_rate_boiler",
    ): "boiler loop flow from the boiler temperature difference",
    (
        "boiler_control",
        "threshold_to_switch_off_boiler",
    ): "switch-off threshold at the supply set point + 5 K",
    (
        "radiator",
        "VWat",
    ): "water volume 5.8e-6 m3/W as in RadiatorEN442_2, was ten times too large",
    (
        "temperature_sensor",
        "m_flow_nominal",
    ): "own nominal flow instead of a placeholder",
    (
        "three_way_valve",
        "m_flow_nominal",
    ): "default consistent with the default radiator and pump",
    (
        "valve",
        "m_flow_nominal",
    ): "default consistent with the default radiator and pump",
}
"""Hydronic parameters corrected in trano 0.39 (trano #39), not set by ifctrano."""


@pytest.fixture(scope="module")
def example_hom_building() -> Building:
    return Building.from_ifc(SPACE_BOUNDARY_IFC / "ExampleHOM.ifc")


def _model(case: str, directory: Path) -> str:
    hvac = None
    if case == "example_hom_heating":
        hvac = [example_hom_heating.write(directory / "ExampleHOM_heating.ifc")]
    building = Building.from_ifc(SPACE_BOUNDARY_IFC / CASES[case], hvac_file_paths=hvac)
    return str(building.create_network("Buildings", NORTH).model())


def _corrected_azimuth(azimuth: float) -> float:
    """Azimuth written before the correction (bearing in radians) corrected."""
    return bearing_to_azimuth(math.degrees(azimuth))


COMPONENT_TYPES = sorted(
    {
        "boiler",
        "boiler_control",
        "collector_control",
        "emission_control",
        "pump",
        "radiator",
        "split_valve",
        "temperature_sensor",
        "three_way_valve",
        "three_way_valve_control",
        "valve",
    },
    key=len,
    reverse=True,
)


def _component_type(name: str) -> str:
    """Type of a component named ``<type>_<id>`` (``valve_space_wc4_pwg``)."""
    return next(type_ for type_ in COMPONENT_TYPES if name.startswith(f"{type_}_"))


@pytest.mark.parametrize(
    ("bearing", "azimuth"),
    [
        (0, NORTH_AZIMUTH),
        (90, EAST),
        (180, SOUTH),
        (270, WEST),
        (360, NORTH_AZIMUTH),
        (45, -2.36),
        (135, -0.79),
        (225, 0.79),
        (315, 2.36),
    ],
)
def test_bearing_to_azimuth(bearing: float, azimuth: float) -> None:
    assert bearing_to_azimuth(bearing) == azimuth


@pytest.mark.parametrize("degrees", range(0, 360, 5))
def test_azimuth_of_outward_normal(degrees: int) -> None:
    """The azimuth of an outward normal is atan2(-x, -y) (Buildings convention)."""
    normal = Vector(
        x=math.cos(math.radians(degrees)), y=math.sin(math.radians(degrees)), z=0
    )
    expected = math.atan2(-normal.x, -normal.y)
    azimuth = bearing_to_azimuth(normal.angle(NORTH))
    # Vector.angle truncates to whole degrees and azimuths have two decimals.
    tolerance = math.radians(1) + 0.005
    assert math.isclose(
        math.remainder(azimuth - expected, 2 * math.pi), 0, abs_tol=tolerance
    )


def _facade_azimuth(x: float, y: float) -> Optional[float]:
    """Azimuth of the ExampleHOM facade a point lies on (footprint 8.58 m x 11.34 m)."""
    facades = {
        SOUTH: abs(y),
        NORTH_AZIMUTH: abs(y - 11.34),
        WEST: abs(x),
        EAST: abs(x - 8.58),
    }
    azimuth, distance = min(facades.items(), key=lambda facade: facade[1])
    return azimuth if distance < 0.1 else None


def test_window_azimuths_follow_the_facades(example_hom_building: Building) -> None:
    """Each window faces the facade it is in, for the configuration and the model."""
    expected: dict[str, set[Optional[float]]] = {}
    for space_boundaries in example_hom_building.space_boundaries:
        space = space_boundaries.space
        for boundary in space_boundaries.boundaries:
            if boundary.entity.is_a("IfcWindow"):
                centroid = boundary.bounding_box.centroid
                expected.setdefault(space.space_unique_name(), set()).add(
                    _facade_azimuth(centroid.x, centroid.y)
                )
    assert expected, "ExampleHOM has windows"
    assert set().union(*expected.values()) == {
        SOUTH,
        WEST,
        NORTH_AZIMUTH,
        EAST,
    }

    config = {
        space["id"]: {
            window["azimuth"] for window in space["external_boundaries"]["windows"]
        }
        for space in example_hom_building.to_config()["spaces"]
    }
    assert {space: config[space] for space in expected} == expected

    spaces = {
        node.name: node
        for node in example_hom_building.create_network().graph.nodes
        if isinstance(node, TranoSpace)
    }
    windows = {
        name: {
            boundary.azimuth
            for boundary in space.external_boundaries
            if isinstance(boundary, Window)
        }
        for name, space in spaces.items()
    }
    assert {
        name: azimuths for name, azimuths in windows.items() if azimuths
    } == expected


def test_azimuths_follow_the_north_axis(example_hom_building: Building) -> None:
    """With north along +x, the facade at x=8.58 (east with north along +y) faces north."""
    config = example_hom_building.to_config(north_axis=Vector(x=1, y=0, z=0))
    windows = {
        space["id"]: {
            window["azimuth"] for window in space["external_boundaries"]["windows"]
        }
        for space in config["spaces"]
    }
    assert windows["space_wc4_pwg"] == {NORTH_AZIMUTH}
    assert windows["space_kitchen5_dsw"] == {EAST, SOUTH}


def test_horizontal_surfaces_face_south(example_hom_building: Building) -> None:
    config = example_hom_building.to_config()
    roofs = [
        wall
        for space in config["spaces"]
        for wall in space["external_boundaries"]["external_walls"]
        if wall["tilt"] != "wall"
    ]
    assert roofs
    assert {roof["azimuth"] for roof in roofs} == {HORIZONTAL_AZIMUTH}


@pytest.mark.parametrize("case", CASES)
def test_physics_snapshot(case: str, tmp_path: Path) -> None:
    """The physical parameters of the generated model do not change."""
    actual = physics(_model(case, tmp_path))
    path = PHYSICS_PATH / f"{case}.json"
    if OVERWRITE_RESULTS:
        dump(actual, path)
    assert not DeepDiff(load(path), actual, math_epsilon=TOLERANCE)


def _changes(before: dict[str, Any], after: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (_component_type(component), parameter)
        for component in before.keys() | after.keys()
        for parameter in before.get(component, {}).keys()
        | after.get(component, {}).keys()
        if before.get(component, {}).get(parameter)
        != after.get(component, {}).get(parameter)
    }


@pytest.mark.parametrize("case", CASES)
def test_only_orientations_and_trano_fixes_changed(case: str) -> None:
    """Compared with trano 0.35, only the corrected azimuths and trano #39 changed.

    The envelope (areas, tilts, constructions and their layers) and the heating
    sizing made by ifctrano are those generated before the upgrade.
    """
    before = load(PHYSICS_PATH / "before_azimuth_fix.json")[case]
    after = load(PHYSICS_PATH / f"{case}.json")

    for zone in before["zones"].values():
        for surface in zone["surfaces"]:
            if "azimuth" in surface:
                surface["azimuth"] = _corrected_azimuth(surface["azimuth"])
    assert not DeepDiff(
        before["zones"], after["zones"], ignore_order=True, math_epsilon=TOLERANCE
    )
    assert before["constructions"] == after["constructions"]

    changes = _changes(before["heating"], after["heating"])
    assert changes <= TRANO_0_39_HYDRONIC_FIXES.keys()
    for component, parameters in after["heating"].items():
        if _component_type(component) == "radiator":
            assert parameters["VWat"] == pytest.approx(
                before["heating"][component]["VWat"] / 10
            )
            assert (
                parameters["Q_flow_nominal"]
                == before["heating"][component]["Q_flow_nominal"]
            )
