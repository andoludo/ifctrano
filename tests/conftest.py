from pathlib import Path

import ifcopenshell
import pytest
from ifcopenshell import file

SPACE_BOUNDARY_IFC = Path(__file__).parent / "models" / "space_boundary"


@pytest.fixture
def duplex_appartment_path() -> Path:
    return SPACE_BOUNDARY_IFC / "Duplex_A.ifc"


@pytest.fixture
def duplex_appartment(duplex_appartment_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment_path))
    return ifcopenshell_file


@pytest.fixture
def two_zone_path() -> Path:
    return SPACE_BOUNDARY_IFC / "TwoZones.ifc"


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
def office_building(office_building_path: Path) -> file:
    ifcopenshell_file = ifcopenshell.open(str(office_building_path))
    return ifcopenshell_file
