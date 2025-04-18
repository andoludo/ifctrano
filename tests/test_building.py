import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from ifctrano.building import Building
from tests.conftest import compare

SHOW_FIGURES = False

def test_building_two_zone(request, two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_model()
    assert compare(building, request)


def test_building_duplex_apartment(request, duplex_apartment_path: Path) -> None:
    building = Building.from_ifc(duplex_apartment_path)
    if SHOW_FIGURES:
        building.show()
    assert compare(building, request)



def test_building_multizone(request, multizone_path: Path) -> None:
    building = Building.from_ifc(multizone_path)
    if SHOW_FIGURES:
        building.show()
    assert compare(building, request)
    assert building.create_model()


def test_building_residential_house(request,residential_house_path: Path) -> None:
    building = Building.from_ifc(residential_house_path)
    if SHOW_FIGURES:
        building.show()

    assert building.create_model()
    assert compare(building, request)

def test_building_two_zone_save_file(two_zone_path: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        temp_ifc_file = Path(temp_dir) / two_zone_path.name
        shutil.copy(two_zone_path, temp_ifc_file)
        building = Building.from_ifc(temp_ifc_file)
        building.save_model()
        assert temp_ifc_file.parent.joinpath(f"{building.name}.mo").exists()


def test_building_two_zone_adjacency(request, two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    assert compare(building.internal_elements, request)


def test_multizone_internal_elements_1(request, multizone_path: Path) -> None:
    building = Building.from_ifc(
        multizone_path,
        selected_spaces_global_id=["3iLI4eTzPsHe5kCfE8mHt4", "0JuRo7Utw1He5uTVScZaH1"],
    )
    assert compare(building.internal_elements, request)

def test_multizone_internal_elements_2(request, multizone_path: Path) -> None:
    building = Building.from_ifc(
        multizone_path,
        selected_spaces_global_id=["3RVyJb7CyAJR86_EwiHH8c", "0JuRo7Utw1He5uTVScZaH1"],
    )
    assert compare(building.internal_elements, request)

def test_multizone_internal_duplex(request,duplex_apartment_path: Path) -> None:
    building = Building.from_ifc(
        duplex_apartment_path,
        selected_spaces_global_id=[
            "0BTBFw6f90Nfh9rP1dlXr2",
            "0BTBFw6f90Nfh9rP1dlXr$",
            "10mjSDZJj9gPS2PrQaxa4o",
            "0BTBFw6f90Nfh9rP1dl_3Q",
        ],
    )
    assert building.create_model()
    assert compare(building.internal_elements, request)

@pytest.mark.skip("too slow")
def test_smiley_west(smiley_west_path: Path) -> None:
    building = Building.from_ifc(smiley_west_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_model()
