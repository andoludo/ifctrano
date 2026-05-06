import ifcopenshell
from ifcopenshell import file

from ifctrano.construction import Materials, Layers, Constructions

from ifctrano.utils import get_building_elements


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


def test_layers_from_ifc_handles_optional_material() -> None:
    """``IfcMaterialLayer.Material`` is OPTIONAL per the IFC schema. The
    parser must fall back to a default material instead of crashing."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    real_material = ifc_file.create_entity("IfcMaterial", Name="Concrete")
    layer_with_material = ifc_file.create_entity(
        "IfcMaterialLayer", Material=real_material, LayerThickness=0.2
    )
    layer_without_material = ifc_file.create_entity(
        "IfcMaterialLayer", Material=None, LayerThickness=0.1
    )

    materials = Materials.from_ifc_materials([real_material])
    layers = Layers.from_ifc_material_layers(
        [layer_with_material, layer_without_material], materials
    )

    assert len(layers.layers) == 2
    assert layers.layers[0].material.name.lower() == "concrete"
    assert layers.layers[1].material.name.startswith("default_material_")
