from ifcopenshell import file

from ifctrano.base import Vector
from ifctrano.bounding_box import OrientedBoundingBox
from ifctrano.space_boundary import initialize_tree, SpaceBoundaries, Space


def test_intersection_space_door(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_appartment.by_guid("1s1jVhK8z0pgKYcr9jt781")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    assert intersection.description() == (2.2886707467062, [-0.0, 1.0, -0.0])


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
        (2.2886707467062, (-0.0, 1.0, -0.0), "1s1jVhK8z0pgKYcr9jt781", "IfcDoor"),
        (7.3926776418866815, (0.0, 0.0, 1.0), "1hOSvn6df7F8_7GcBWlRqU", "IfcSlab"),
        (9.247723, (-1.0, -0.0, -0.0), "2O2Fr$t4X7Zf8NOew3FNld", "IfcWallStandardCase"),
        (11.700699999999998, (-0.0, 1.0, -0.0), "1hOSvn6df7F8_7GcBWlR72", "IfcWindow"),
        (
            12.344923000000001,
            (1.0, 0.0, 0.0),
            "2O2Fr$t4X7Zf8NOew3FNqI",
            "IfcWallStandardCase",
        ),
        (14.925923, (-0.0, 1.0, -0.0), "2O2Fr$t4X7Zf8NOew3FNtn", "IfcWallStandardCase"),
        (18.343008663780722, (0.0, 0.0, 1.0), "1hOSvn6df7F8_7GcBWlRrM", "IfcSlab"),
        (27.660089, (-0.0, -0.0, -1.0), "2O2Fr$t4X7Zf8NOew3FK4F", "IfcSlab"),
        (27.660089000000003, (-0.0, -0.0, -1.0), "2OBrcmyk58NupXoVOHUtgP", "IfcSlab"),
    ]


def test_get_space_boundaries_another_space(duplex_appartment: file) -> None:
    tree = initialize_tree(duplex_appartment)
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    boundaries = SpaceBoundaries.from_space_entity(duplex_appartment, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (
            0.5117823028019094,
            (-0.0, -0.0, -1.0),
            "2O2Fr$t4X7Zf8NOew3FNtn",
            "IfcWallStandardCase",
        ),
        (
            0.5117823028019096,
            (0.0, 0.0, 1.0),
            "0jf0rYHfX3RAB3bSIRjmmy",
            "IfcWallStandardCase",
        ),
        (
            0.6198863941376016,
            (-0.074653364, 0.9972095443, 0.0),
            "1hOSvn6df7F8_7GcBWlSga",
            "IfcWindow",
        ),
        (
            0.6198863941376019,
            (-0.074653364, 0.9972095443, 0.0),
            "1hOSvn6df7F8_7GcBWlSnC",
            "IfcWindow",
        ),
        (
            0.6198863941376019,
            (-0.074653364, 0.9972095443, 0.0),
            "1hOSvn6df7F8_7GcBWlSp1",
            "IfcWindow",
        ),
        (
            1.212751258931948,
            (0.0, 0.0, 1.0),
            "0jf0rYHfX3RAB3bSIRjmr1",
            "IfcWallStandardCase",
        ),
        (
            1.2127512589319482,
            (-0.0, -0.0, -1.0),
            "2O2Fr$t4X7Zf8NOew3FNhv",
            "IfcWallStandardCase",
        ),
        (
            1.5020278967377458,
            (-0.9972095443, -0.0746533647, 0.0),
            "2O2Fr$t4X7Zf8NOew3FLIE",
            "IfcWallStandardCase",
        ),
        (1.5961919833253146, (-0.0, -0.0, -1.0), "2OBrcmyk58NupXoVOHUt8s", "IfcSlab"),
        (
            1.6453957480957717,
            (-0.9972095443, -0.074653364, 0.0),
            "1l0GAJtRTFv8$zmKJOH4ZZ",
            "IfcWindow",
        ),
        (
            2.1165014480693323,
            (0.074653364, -0.9972095443, -0.0),
            "1hOSvn6df7F8_7GcBWlSFK",
            "IfcDoor",
        ),
        (
            4.1669786929861665,
            (0.074653364, -0.9972095443, -0.0),
            "2O2Fr$t4X7Zf8NOew3FLMr",
            "IfcWallStandardCase",
        ),
        (
            5.4222408304601215,
            (0.074653364, -0.9972095443, -0.0),
            "2O2Fr$t4X7Zf8NOew3FLTF",
            "IfcWallStandardCase",
        ),
        (
            6.729170004927727,
            (-0.074653364, 0.9972095443, 0.0),
            "1hOSvn6df7F8_7GcBWlSXO",
            "IfcWindow",
        ),
        (
            10.640091421705847,
            (-0.0746533641, 0.9972095443, 0.0),
            "2O2Fr$t4X7Zf8NOew3FLQD",
            "IfcWallStandardCase",
        ),
        (
            16.110280449815555,
            (0.9972095443, 0.0746533639, -0.0),
            "2O2Fr$t4X7Zf8NOew3FKau",
            "IfcWall",
        ),
        (
            16.798121335918182,
            (-0.9972095443, -0.0746533639, 0.0),
            "2O2Fr$t4X7Zf8NOew3FLPP",
            "IfcWallStandardCase",
        ),
        (24.511075501663456, (-0.0, -0.0, -1.0), "1hOSvn6df7F8_7GcBWlRqU", "IfcSlab"),
        (25.94542685522518, (-0.0, -0.0, -1.0), "2OBrcmyk58NupXoVOHUtC0", "IfcSlab"),
        (26.545228088276954, (0.0, 0.0, 1.0), "3ThA22djr8AQQ9eQMA5s7I", "IfcSlab"),
    ]


def test_intersection_another_space_window(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_appartment.by_guid("1hOSvn6df7F8_7GcBWlSXO")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    assert intersection.description() == (
        6.729170004927727,
        [-0.074653364, 0.9972095443, 0.0],
    )


def test_intersection_another_space_small_window(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_appartment.by_guid("1hOSvn6df7F8_7GcBWlSnC")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    assert intersection.description() == (
        0.6198863941376019,
        [-0.074653364, 0.9972095443, 0.0],
    )


def test_get_space_boundaries_two_zones(two_zones: file) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (1.0119311581000008, (0.0, -1.0, 0.0), "3_bV5rUcEqG8kASS9SeipQ", "IfcWindow"),
        (2.0304246004626076, (-0.0, 1.0, -0.0), "0t6bnTN6rtIuKOrcjLzg0Z", "IfcDoor"),
        (
            8.999999999999998,
            (-1.0, -0.0, -0.0),
            "0iF2lvyBzlJgGtYWNfuhrr",
            "IfcWallStandardCase",
        ),
        (
            8.999999999999998,
            (1.0, 0.0, 0.0),
            "3PvpR$hKFlHuhmlmbygBig",
            "IfcWallStandardCase",
        ),
        (9.0, (0.0, -1.0, 0.0), "1vV1tvb7ErHeOK_7Z$PfBe", "IfcWallStandardCase"),
        (9.0, (-0.0, 1.0, -0.0), "0JPvTpQNrcIf4SV9z30TQ6", "IfcWallStandardCase"),
        (9.000000000000002, (-0.0, -0.0, -1.0), "2wnKoR7TlMJAMsrOjFIt2k", "IfcSlab"),
        (9.000000000000002, (0.0, 0.0, 1.0), "1GtdW14ne2HvZSwZg9DViT", "IfcSlab"),
    ]


def test_space_paramaters(two_zones: file) -> None:
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    space_ = Space.from_entity(space)
    assert space_.check_volume()


def test_space_paramaters_another(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    space_ = Space.from_entity(space)
    assert not space_.check_volume()  # TODO: why?


def test_space_paramaters_another_space(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dlXri")
    space_ = Space.from_entity(space)
    assert space_.check_volume()


def test_intersection_space_space(two_zones: file) -> None:
    space_1 = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    space_2 = two_zones.by_guid("3NzGTD1DeLJR3FlSqrXdUp")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert intersection.description() == (9.0, [-0.0, 1.0, -0.0])


def test_intersection_space_windows_multizone(multizone: file) -> None:
    space_1 = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    space_2 = multizone.by_guid("1cMdolzEBzHfSYIkD4K2Kb")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert intersection.description() == (39.22227235752945, [-1.0, -0.0, -0.0])


def test_get_space_boundaries_multizone(multizone: file) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (2.50823021632346, (0.0, -1.0, 0.0), "19B65EIi3EIh2tA$vM8ZgT", "IfcDoor"),
        (2.508997869619421, (1.0, 0.0, 0.0), "0jryqJ3XdhIf5exNfKRiH5", "IfcDoor"),
        (7.76210139838769, (-0.0, 1.0, -0.0), "1X7PJ2zxFYJQJ7zr1nDhxn", "IfcWindow"),
        (21.6, (0.0, -1.0, 0.0), "2Mx5O979lPJu$FydjHS6_e", "IfcWallStandardCase"),
        (21.6, (-0.0, 1.0, -0.0), "0gSvHU18p4HuqD4mS$gG8D", "IfcWallStandardCase"),
        (39.22227235752945, (-1.0, -0.0, -0.0), "1cMdolzEBzHfSYIkD4K2Kb", "IfcWindow"),
        (50.22, (-1.0, -0.0, -0.0), "1116XLLwKdJRZmM_rK_l4f", "IfcWallStandardCase"),
        (50.22, (1.0, 0.0, 0.0), "0idtIsso1oHPkD7tQ4ezLe", "IfcWallStandardCase"),
        (148.79999999999998, (-0.0, -0.0, -1.0), "2f4B0EKma$Gf_OoOWMssbl", "IfcSlab"),
        (148.79999999999998, (0.0, 0.0, 1.0), "1Hey_hGXaaIvKh948Y5lwS", "IfcSlab"),
    ]


def test_get_space_boundaries_two_zones_slab(two_zones: file) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    trano_space = boundaries.model([], Vector(x=0, y=1, z=0))
    floor = next(e for e in trano_space.external_boundaries if e.tilt.value == "floor")
    roof = next(e for e in trano_space.external_boundaries if e.tilt.value == "ceiling")
    assert "IfcSlab_1gtdw14ne2hvzswzg9dvit" in roof.name
    assert "IfcSlab_2wnkor7tlmjamsrojfit2k" in floor.name
    assert int(roof.surface) == 9
    assert int(floor.surface) == 9
