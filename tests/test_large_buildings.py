from pathlib import Path

import pytest
from _pytest.fixtures import FixtureRequest

from ifctrano.building import Building
from tests.conftest import compare

SHOW_FIGURES = False


@pytest.mark.large
def test_smiley_west(request: FixtureRequest, smiley_west_path: Path) -> None:
    building = Building.from_ifc(smiley_west_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_network()
    assert compare(building, request)


@pytest.mark.large
def test_office_building(request: FixtureRequest, office_building_path: Path) -> None:
    building = Building.from_ifc(office_building_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_network()
    assert compare(building, request)


@pytest.mark.large
def test_digital_hub(request: FixtureRequest, digital_hub_path: Path) -> None:
    building = Building.from_ifc(digital_hub_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_network()
    assert compare(building, request)


@pytest.mark.large
def test_erc(request: FixtureRequest, erc_path: Path) -> None:
    building = Building.from_ifc(erc_path)
    if SHOW_FIGURES:
        building.show()
    assert building.create_network()
    assert compare(building, request)
