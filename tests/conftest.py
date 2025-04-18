from pathlib import Path

import ifcopenshell
import pytest
from ifcopenshell import file

SPACE_BOUNDARY_IFC = Path(__file__).parent / "models" / "space_boundary"

SHOW_FIGURES=False
OVERWRITE_RESULTS = False
TEST_PATH = Path(__file__).parent.joinpath("data")
TEST_PATH.mkdir(parents=True, exist_ok=True)

def compare(elements, request):
    if elements is None:
        raise ValueError("No intersection found")
    file_path = TEST_PATH.joinpath(f"{request.node.name}.json")
    if OVERWRITE_RESULTS:
        elements.save_description(file_path)
    return elements.description_loaded() == elements.load_description(file_path)

@pytest.fixture
def duplex_apartment_path() -> Path:
    return SPACE_BOUNDARY_IFC / "Duplex_A.ifc"


@pytest.fixture
def duplex_apartment(duplex_apartment_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(duplex_apartment_path))
    return ifcopenshell_file


@pytest.fixture
def two_zone_path() -> Path:
    return SPACE_BOUNDARY_IFC / "TwoZones.ifc"


@pytest.fixture
def smiley_west_path() -> Path:
    return SPACE_BOUNDARY_IFC / "AC-20-Smiley-West-10-Bldg.ifc"


@pytest.fixture
def smiley_west(smiley_west_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(smiley_west_path))
    return ifcopenshell_file


@pytest.fixture
def two_zones(two_zone_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(two_zone_path))
    return ifcopenshell_file


@pytest.fixture
def multizone_path() -> Path:
    return SPACE_BOUNDARY_IFC / "MultiZoneBuilding.ifc"


@pytest.fixture
def multizone(multizone_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(multizone_path))
    return ifcopenshell_file


@pytest.fixture
def office_building_path() -> Path:
    return SPACE_BOUNDARY_IFC / "Office Building.ifc"


@pytest.fixture
def residential_house_path() -> Path:
    return SPACE_BOUNDARY_IFC / "Residential House.ifc"

@pytest.fixture
def residential_house(residential_house_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(residential_house_path))
    return ifcopenshell_file

@pytest.fixture
def office_building(office_building_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(office_building_path))
    return ifcopenshell_file


