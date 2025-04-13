import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from ifctrano.building import Building


def test_building_two_zone(two_zone_path: Path) -> None:
    building = Building.from_ifc(two_zone_path)
    space_boundaries = building.get_boundaries("0t8Y4TnjqtGRnTw6NPeuj9")
    internal_element_ids = building.internal_elements.internal_element_ids()
    assert building.create_model()
    assert [
        b.description()
        for b in space_boundaries.boundaries
        if b.entity.GlobalId not in internal_element_ids
    ] == [
        (
            8.999999999999998,
            (1.0, 0.0, 0.0),
            "3PvpR$hKFlHuhmlmbygBig",
            "IfcWallStandardCase",
        ),
        (9.000000000000002, (-0.0, -0.0, -1.0), "2wnKoR7TlMJAMsrOjFIt2k", "IfcSlab"),
        (9.000000000000002, (0.0, 0.0, 1.0), "1GtdW14ne2HvZSwZg9DViT", "IfcSlab"),
        (
            8.999999999999998,
            (-1.0, -0.0, -0.0),
            "0iF2lvyBzlJgGtYWNfuhrr",
            "IfcWallStandardCase",
        ),
        (1.0119311581000008, (0.0, -1.0, 0.0), "3_bV5rUcEqG8kASS9SeipQ", "IfcWindow"),
        (9.0, (0.0, -1.0, 0.0), "1vV1tvb7ErHeOK_7Z$PfBe", "IfcWallStandardCase"),
    ]


def test_duplex_appartment(duplex_appartment_path: Path) -> None:
    building = Building.from_ifc(duplex_appartment_path)

    assert building.create_model()


def test_multizone(multizone_path: Path) -> None:
    building = Building.from_ifc(multizone_path)
    space_boundaries = building.get_boundaries("3iLI4eTzPsHe5kCfE8mHt4")
    internal_element_ids = building.internal_elements.internal_element_ids()
    assert [
        b.description()
        for b in space_boundaries.boundaries
        if b.entity.GlobalId not in internal_element_ids
    ] == [
        (21.6, (-0.0, 1.0, -0.0), "0gSvHU18p4HuqD4mS$gG8D", "IfcWallStandardCase"),
        (148.79999999999998, (0.0, 0.0, 1.0), "1Hey_hGXaaIvKh948Y5lwS", "IfcSlab"),
        (148.79999999999998, (-0.0, -0.0, -1.0), "2f4B0EKma$Gf_OoOWMssbl", "IfcSlab"),
        (50.22, (-1.0, -0.0, -0.0), "1116XLLwKdJRZmM_rK_l4f", "IfcWallStandardCase"),
        (7.76210139838769, (-0.0, 1.0, -0.0), "1X7PJ2zxFYJQJ7zr1nDhxn", "IfcWindow"),
        (39.22227235752945, (-1.0, -0.0, -0.0), "1cMdolzEBzHfSYIkD4K2Kb", "IfcWindow"),
    ]
    assert building.create_model()


def test_residential_house_path(residential_house_path: Path) -> None:
    building = Building.from_ifc(residential_house_path)
    assert building.create_model()


def test_building_two_zone_save_file(two_zone_path: Path) -> None:
    with TemporaryDirectory() as temp_dir:
        temp_ifc_file = Path(temp_dir) / two_zone_path.name
        shutil.copy(two_zone_path, temp_ifc_file)
        building = Building.from_ifc(temp_ifc_file)
        building.save_model()
        assert temp_ifc_file.parent.joinpath(f"{building.name}.mo").exists()


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


def test_multizone_internal_duplex(duplex_appartment_path: Path) -> None:
    building = Building.from_ifc(
        duplex_appartment_path,
        selected_spaces_global_id=[
            "0BTBFw6f90Nfh9rP1dlXr2",
            "0BTBFw6f90Nfh9rP1dlXr$",
            "10mjSDZJj9gPS2PrQaxa4o",
            "0BTBFw6f90Nfh9rP1dl_3Q",
        ],
    )
    assert building.internal_elements
    assert building.create_model()
