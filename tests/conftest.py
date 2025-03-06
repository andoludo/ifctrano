from pathlib import Path

import ifcopenshell
import pytest
from ifcopenshell import file

SPACE_BOUNDARY_IFC = Path(__file__).parent / "models" / "space_boundary"


@pytest.fixture
def duplex_appartment() -> file:
    duplex_appartment = SPACE_BOUNDARY_IFC / "Duplex_A.ifc"
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment))
    return ifcopenshell_file


@pytest.fixture
def two_zones() -> file:
    duplex_appartment = SPACE_BOUNDARY_IFC / "TwoZones.ifc"
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment))
    return ifcopenshell_file