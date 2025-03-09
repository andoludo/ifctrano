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

def test_multizone(multizone_path: Path) -> None:
    building = Building.from_ifc(multizone_path)
    assert building.create_model()

def test_building_two_zone_save_file(two_zone_path: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        temp_ifc_file = Path(temp_dir) / two_zone_path.name
        shutil.copy(two_zone_path, temp_ifc_file)
        building = Building.from_ifc(temp_ifc_file)
        building.save_model()
        assert temp_ifc_file.parent.joinpath(f"{temp_ifc_file.stem}.mo").exists()


def test_building_two_zone_adjacency(two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    assert building.internal_elements.description() == [
        (
            "0t8Y4TnjqtGRnTw6NPeuj9",
            "3NzGTD1DeLJR3FlSqrXdUp",
            "0JPvTpQNrcIf4SV9z30TQ6",
            "IfcWallStandardCase",
            9.0,
        ),
        (
            "0t8Y4TnjqtGRnTw6NPeuj9",
            "3NzGTD1DeLJR3FlSqrXdUp",
            "0t6bnTN6rtIuKOrcjLzg0Z",
            "IfcDoor",
            2.026556059721071,
        ),
    ]


def test_multizone_internal_elements_1(multizone_path: Path) -> None:
    building = Building.from_ifc(
        multizone_path,
        selected_spaces_global_id=["3iLI4eTzPsHe5kCfE8mHt4", "0JuRo7Utw1He5uTVScZaH1"],
    )
    assert building.internal_elements.description() == [
        (
            "0JuRo7Utw1He5uTVScZaH1",
            "3iLI4eTzPsHe5kCfE8mHt4",
            "0idtIsso1oHPkD7tQ4ezLe",
            "IfcWallStandardCase",
            50.22,
        ),
        (
            "0JuRo7Utw1He5uTVScZaH1",
            "3iLI4eTzPsHe5kCfE8mHt4",
            "0jryqJ3XdhIf5exNfKRiH5",
            "IfcDoor",
            2.508230216072762,
        ),
    ]


def test_multizone_internal_elements_2(multizone_path: Path) -> None:
    building = Building.from_ifc(
        multizone_path,
        selected_spaces_global_id=["3RVyJb7CyAJR86_EwiHH8c", "0JuRo7Utw1He5uTVScZaH1"],
    )
    assert building.internal_elements.description() == [
        (
            "0JuRo7Utw1He5uTVScZaH1",
            "3RVyJb7CyAJR86_EwiHH8c",
            "0uVX8vfyEJJAaRUqykVCMg",
            "IfcDoor",
            2.5082302158191934,
        ),
        (
            "0JuRo7Utw1He5uTVScZaH1",
            "3RVyJb7CyAJR86_EwiHH8c",
            "1JO56TA8lfJuVyUb54GJXA",
            "IfcWallStandardCase",
            8.100000000000001,
        ),
    ]
