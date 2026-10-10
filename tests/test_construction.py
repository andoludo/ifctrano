import re

import ifcopenshell
import pytest
from ifcopenshell import file

from ifctrano.construction import Materials, Layers, Constructions

from ifctrano.utils import get_building_elements, modelica_identifier
from tests.conftest import SPACE_BOUNDARY_IFC

MODELICA_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def test_materials(two_zones: file) -> None:
    materials = two_zones.by_type("IfcMaterial")
    materials_ = Materials.from_ifc_materials(materials)
    assert materials_.materials


def test_material_layer(two_zones: file) -> None:
    material_layers = two_zones.by_type("IfcMaterialLayer")
    materials = Materials.from_ifc_materials(two_zones.by_type("IfcMaterial"))
    layers = Layers.from_ifc_material_layers(material_layers, materials)
    assert layers.layers


def test_construction(two_zones: file) -> None:
    constructions = Constructions.from_ifc(two_zones)
    assert constructions.constructions


def test_construction_two_zones(two_zones: file) -> None:
    constructions = Constructions.from_ifc(two_zones)
    for wall in get_building_elements(two_zones):
        construction = constructions.get_construction(wall)
        assert construction.layers


def test_construction_duplex_apartment(duplex_apartment: file) -> None:
    constructions = Constructions.from_ifc(duplex_apartment)
    for wall in get_building_elements(duplex_apartment):
        construction = constructions.get_construction(wall)
        assert construction.layers


def test_construction_multizone(multizone: file) -> None:
    constructions = Constructions.from_ifc(multizone)
    for wall in get_building_elements(multizone):
        construction = constructions.get_construction(wall)
        assert construction.layers


def test_construction_sample_house(sample_house: file) -> None:
    constructions = Constructions.from_ifc(sample_house)
    for wall in get_building_elements(sample_house):
        construction = constructions.get_construction(wall)
        assert construction.layers


def test_construction_example_hom(example_hom: file) -> None:
    constructions = Constructions.from_ifc(example_hom)
    for wall in get_building_elements(example_hom):
        construction = constructions.get_construction(wall)
        assert construction.layers


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cavity wall", "cavity_wall"),
        ("Mauerwerk-24", "mauerwerk24"),
        ("10mm gypsum", "construction_10mm_gypsum"),
        (None, "construction_42"),
        ("", "construction_42"),
    ],
)
def test_modelica_identifier(text: str | None, expected: str) -> None:
    assert modelica_identifier(text, "construction_42") == expected


def test_construction_names_are_stable_modelica_identifiers() -> None:
    """Unnamed layer sets (as in ExampleHOM.ifc) used to get random names,
    which made models unreproducible and, when starting with a digit,
    impossible to load in Modelica."""
    ifc_file = ifcopenshell.open(str(SPACE_BOUNDARY_IFC / "ExampleHOM.ifc"))
    names = [c.name for c in Constructions.from_ifc(ifc_file).constructions]
    again = [c.name for c in Constructions.from_ifc(ifc_file).constructions]
    assert names == again
    assert all(MODELICA_IDENTIFIER.match(name) for name in names), names


def test_construction_names_are_unique() -> None:
    """Layer sets sharing a name (Background Fill 350 of 350 and 350.5 mm) get
    distinct names, so the configuration has no duplicate construction."""
    ifc_file = ifcopenshell.open(
        str(SPACE_BOUNDARY_IFC / "RooftopBuilding3ZonesThin.ifc")
    )
    names = [c.name for c in Constructions.from_ifc(ifc_file).constructions]
    assert len(names) == len(set(names))
    assert {"background_fill_350", "background_fill_350_88204"} <= set(names)
