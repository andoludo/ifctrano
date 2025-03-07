import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from ifctrano.building import Building


def test_building_two_zone(two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    assert building.create_model()


def test_duplex_appartment(duplex_appartment_path: Path) -> None:
    building = Building.from_ifc(duplex_appartment_path)
    assert building.create_model()


def test_building_two_zone_save_file(two_zone_path: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        temp_ifc_file = Path(temp_dir) / two_zone_path.name
        shutil.copy(two_zone_path, temp_ifc_file)
        building = Building.from_ifc(temp_ifc_file)
        building.save_model()
        assert temp_ifc_file.parent.joinpath(f"{temp_ifc_file.stem}.mo").exists()
