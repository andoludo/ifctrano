from pathlib import Path

from ifctrano.building import Building


def test_building_two_zone(two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    assert building.create_model()


def test_duplex_appartment(duplex_appartment_path: Path) -> None:
    building = Building.from_ifc(duplex_appartment_path)
    assert building.create_model()
