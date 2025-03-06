from ifcopenshell import file

from ifctrano.bounding_box import OrientedBoundingBox
from ifctrano.space_boundary import initialize_tree, SpaceBoundaries


def test_intersection_space_door(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_appartment.by_guid("1s1jVhK8z0pgKYcr9jt781")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    assert intersection.description() == (2.288670752342412, [-0.0, 1.0, -0.0])


def test_intersection_space_iinternal_wall(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_appartment.by_guid("2O2Fr$t4X7Zf8NOew3FNld")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    assert intersection.description() == (9.247723, [-1.0, 0.0, 0.0])


def test_get_space_boundaries(duplex_appartment: file) -> None:

    tree = initialize_tree(duplex_appartment)
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    boundaries = SpaceBoundaries.from_space_entity(duplex_appartment, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (2.288670752342412, (-0.0, 1.0, -0.0), "1s1jVhK8z0pgKYcr9jt781", "IfcDoor"),
        (9.247723, (-1.0, 0.0, 0.0), "2O2Fr$t4X7Zf8NOew3FNld", "IfcWallStandardCase"),
        (11.700699999999998, (-0.0, 1.0, -0.0), "1hOSvn6df7F8_7GcBWlR72", "IfcWindow"),
        (
            12.344923000000001,
            (1.0, -0.0, -0.0),
            "2O2Fr$t4X7Zf8NOew3FNqI",
            "IfcWallStandardCase",
        ),
        (14.925923, (-0.0, 1.0, -0.0), "2O2Fr$t4X7Zf8NOew3FNtn", "IfcWallStandardCase"),
        (27.660089, (-0.0, -0.0, -1.0), "2O2Fr$t4X7Zf8NOew3FK4F", "IfcSlab"),
        (27.660089, (-0.0, -0.0, -1.0), "2OBrcmyk58NupXoVOHUtgP", "IfcSlab"),
    ]


def test_get_space_boundaries_another_space(duplex_appartment: file) -> None:

    tree = initialize_tree(duplex_appartment)
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    boundaries = SpaceBoundaries.from_space_entity(duplex_appartment, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (
            0.5117882515270118,
            (-0.0, 0.0, -1.0),
            "2O2Fr$t4X7Zf8NOew3FNtn",
            "IfcWallStandardCase",
        ),
        (
            0.6198863535146009,
            (-0.0746542366, 0.997209479, 0.0),
            "1hOSvn6df7F8_7GcBWlSga",
            "IfcWindow",
        ),
        (
            0.6198863535146013,
            (-0.0746542366, 0.997209479, 0.0),
            "1hOSvn6df7F8_7GcBWlSnC",
            "IfcWindow",
        ),
        (
            0.6198863535146013,
            (-0.0746542366, 0.997209479, 0.0),
            "1hOSvn6df7F8_7GcBWlSp1",
            "IfcWindow",
        ),
        (
            1.2127648338850439,
            (-0.0, 0.0, -1.0),
            "2O2Fr$t4X7Zf8NOew3FNhv",
            "IfcWallStandardCase",
        ),
        (
            1.5020401943031838,
            (-0.997209479, -0.0746542366, -0.0),
            "2O2Fr$t4X7Zf8NOew3FLIE",
            "IfcWallStandardCase",
        ),
        (1.5961969011792818, (-0.0, 0.0, -1.0), "2OBrcmyk58NupXoVOHUt8s", "IfcSlab"),
        (
            1.6453956402680923,
            (-0.997209479, -0.0746542366, -0.0),
            "1l0GAJtRTFv8$zmKJOH4ZZ",
            "IfcWindow",
        ),
        (
            2.1165013078489454,
            (0.0746542366, -0.997209479, -0.0),
            "1hOSvn6df7F8_7GcBWlSFK",
            "IfcDoor",
        ),
        (
            4.166978419911648,
            (0.0746542366, -0.997209479, -0.0),
            "2O2Fr$t4X7Zf8NOew3FLMr",
            "IfcWallStandardCase",
        ),
        (
            5.422248308824379,
            (0.0746542366, -0.997209479, -0.0),
            "2O2Fr$t4X7Zf8NOew3FLTF",
            "IfcWallStandardCase",
        ),
        (
            6.729169563957021,
            (-0.0746542366, 0.997209479, 0.0),
            "1hOSvn6df7F8_7GcBWlSXO",
            "IfcWindow",
        ),
        (
            10.640099978271124,
            (-0.0746542366, 0.997209479, 0.0),
            "2O2Fr$t4X7Zf8NOew3FLQD",
            "IfcWallStandardCase",
        ),
        (
            16.110280152564844,
            (0.997209479, 0.0746542366, 0.0),
            "2O2Fr$t4X7Zf8NOew3FKau",
            "IfcWall",
        ),
        (
            16.798128633940465,
            (-0.997209479, -0.0746542365, -0.0),
            "2O2Fr$t4X7Zf8NOew3FLPP",
            "IfcWallStandardCase",
        ),
        (24.51107058685661, (-0.0, 0.0, -1.0), "1hOSvn6df7F8_7GcBWlRqU", "IfcSlab"),
        (25.94542966166917, (-0.0, 0.0, -1.0), "2OBrcmyk58NupXoVOHUtC0", "IfcSlab"),
    ]


def test_intersection_another_space_window(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_appartment.by_guid("1hOSvn6df7F8_7GcBWlSXO")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    assert intersection.description() == (
        6.729169563957021,
        [-0.0746542366, 0.997209479, 0.0],
    )


def test_intersection_another_space_small_window(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_appartment.by_guid("1hOSvn6df7F8_7GcBWlSnC")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    assert intersection.description() == (
        0.6198863535146013,
        [-0.0746542366, 0.997209479, 0.0],
    )


def test_get_space_boundaries_two_zones(two_zones: file) -> None:

    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (1.0124277731075229, (0.0, -1.0, -0.0), "3_bV5rUcEqG8kASS9SeipQ", "IfcWindow"),
        (2.031548133505456, (-0.0, 1.0, 0.0), "0t6bnTN6rtIuKOrcjLzg0Z", "IfcDoor"),
        (
            9.004393458473391,
            (-0.9995120761, 0.0, -0.0312347524),
            "0iF2lvyBzlJgGtYWNfuhrr",
            "IfcWallStandardCase",
        ),
        (
            9.004393458473391,
            (0.9995120761, -0.0, 0.0312347524),
            "3PvpR$hKFlHuhmlmbygBig",
            "IfcWallStandardCase",
        ),
        (
            9.004393458473393,
            (-0.0, 1.0, 0.0),
            "0JPvTpQNrcIf4SV9z30TQ6",
            "IfcWallStandardCase",
        ),
        (9.281250000000002, (0.0, 0.0, -1.0), "2wnKoR7TlMJAMsrOjFIt2k", "IfcSlab"),
        (9.281250000000002, (-0.0, -0.0, 1.0), "1GtdW14ne2HvZSwZg9DViT", "IfcSlab"),
        (
            9.285780754360212,
            (0.0, -1.0, -0.0),
            "1vV1tvb7ErHeOK_7Z$PfBe",
            "IfcWallStandardCase",
        ),
    ]


def test_to_trano_space(two_zones: file) -> None:

    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)

    boundaries.to_trano_space()