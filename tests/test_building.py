import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from _pytest.fixtures import FixtureRequest

from ifctrano.building import Building
from tests.conftest import compare

SHOW_FIGURES = False


def test_building_two_zone(request: FixtureRequest, two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_example_hom(request: FixtureRequest, example_hom_path: Path) -> None:
    building = Building.from_ifc(example_hom_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_tall_building(request: FixtureRequest, tall_building_path: Path) -> None:
    building = Building.from_ifc(tall_building_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_large_building(request: FixtureRequest, large_building_path: Path) -> None:
    building = Building.from_ifc(large_building_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_sample_house(request: FixtureRequest, sample_house_path: Path) -> None:
    building = Building.from_ifc(sample_house_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_rooftop_building_three_zones_thin(
    request: FixtureRequest, rooftop_building_three_zones_thin_path: Path
) -> None:
    building = Building.from_ifc(rooftop_building_three_zones_thin_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


@pytest.mark.skip("segmentation fault?")
def test_rooftop_building_four_zones_thin(
    request: FixtureRequest, rooftop_building_four_zones_thin_path: Path
) -> None:
    building = Building.from_ifc(rooftop_building_four_zones_thin_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_building_duplex_apartment(
    request: FixtureRequest, duplex_apartment_path: Path
) -> None:
    building = Building.from_ifc(duplex_apartment_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_building_multizone(request: FixtureRequest, multizone_path: Path) -> None:
    building = Building.from_ifc(multizone_path)
    if SHOW_FIGURES:
        building.show()
    assert compare(building, request)
    assert building.get_model()


def test_building_residential_house(
    request: FixtureRequest, residential_house_path: Path
) -> None:
    building = Building.from_ifc(residential_house_path)
    if SHOW_FIGURES:
        building.show()

    assert building.get_model()
    assert compare(building, request)


def test_building_two_zone_save_file(two_zone_path: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        temp_ifc_file = Path(temp_dir) / two_zone_path.name
        shutil.copy(two_zone_path, temp_ifc_file)
        building = Building.from_ifc(temp_ifc_file)
        building.save_model()
        assert temp_ifc_file.parent.joinpath(f"{building.name}.mo").exists()


def test_building_two_zone_adjacency(
    request: FixtureRequest, two_zone_path: Path
) -> None:
    building = Building.from_ifc(two_zone_path)
    assert compare(building.internal_elements, request)


def test_multizone_internal_elements_1(
    request: FixtureRequest, multizone_path: Path
) -> None:
    building = Building.from_ifc(
        multizone_path,
        selected_spaces_global_id=["3iLI4eTzPsHe5kCfE8mHt4", "0JuRo7Utw1He5uTVScZaH1"],
    )
    assert compare(building.internal_elements, request)


def test_multizone_internal_elements_2(
    request: FixtureRequest, multizone_path: Path
) -> None:
    building = Building.from_ifc(
        multizone_path,
        selected_spaces_global_id=["3RVyJb7CyAJR86_EwiHH8c", "0JuRo7Utw1He5uTVScZaH1"],
    )
    assert compare(building.internal_elements, request)


def test_multizone_internal_duplex(
    request: FixtureRequest, duplex_apartment_path: Path
) -> None:
    building = Building.from_ifc(
        duplex_apartment_path,
        selected_spaces_global_id=[
            "0BTBFw6f90Nfh9rP1dlXr2",
            "0BTBFw6f90Nfh9rP1dlXr$",
            "10mjSDZJj9gPS2PrQaxa4o",
            "0BTBFw6f90Nfh9rP1dl_3Q",
        ],
    )
    assert building.get_model()
    assert compare(building.internal_elements, request)


def test_architect(request: FixtureRequest, architect_path: Path) -> None:
    building = Building.from_ifc(architect_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_building_layer(request: FixtureRequest, layer_path: Path) -> None:
    building = Building.from_ifc(layer_path)
    if SHOW_FIGURES:
        building.show()
    assert building.get_model()
    assert compare(building, request)


def test_building_layer_configuration(request: FixtureRequest, layer_path: Path) -> None:
    building = Building.from_ifc(layer_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_configuration()
