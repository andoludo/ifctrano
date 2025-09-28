from _pytest.fixtures import FixtureRequest
from ifcopenshell import file

from ifctrano.base import Vector
from ifctrano.bounding_box import OrientedBoundingBox
from ifctrano.building import get_internal_elements
from ifctrano.construction import Constructions
from ifctrano.space_boundary import initialize_tree, SpaceBoundaries, Space
from tests.conftest import SHOW_FIGURES, compare


def test_intersection_space_door(
    request: FixtureRequest, duplex_apartment: file
) -> None:
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_apartment.by_guid("1s1jVhK8z0pgKYcr9jt781")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_intersection_space_iinternal_wall(
    request: FixtureRequest, duplex_apartment: file
) -> None:
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_apartment.by_guid("2O2Fr$t4X7Zf8NOew3FNld")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_get_space_boundaries(request: FixtureRequest, duplex_apartment: file) -> None:
    tree = initialize_tree(duplex_apartment)
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    boundaries = SpaceBoundaries.from_space_entity(duplex_apartment, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_get_space_boundaries_another_space(
    request: FixtureRequest, duplex_apartment: file
) -> None:

    tree = initialize_tree(duplex_apartment)
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    boundaries = SpaceBoundaries.from_space_entity(duplex_apartment, tree, space)
    if SHOW_FIGURES:
        boundaries.show()

    assert compare(boundaries, request)


def test_get_space_boundaries_another_space_0BTBFw6f90Nfh9rP1dl_3A(  # noqa: N802
    request: FixtureRequest, duplex_apartment: file
) -> None:
    tree = initialize_tree(duplex_apartment)
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_3A")
    boundaries = SpaceBoundaries.from_space_entity(duplex_apartment, tree, space)
    boundaries.model(
        [], Vector(x=0, y=1, z=0), Constructions.from_ifc(duplex_apartment)
    )
    if SHOW_FIGURES:
        boundaries.show()

    assert compare(boundaries, request)


def test_get_space_boundaries_another_space_0pNy6pOyf7JPmXRLgxs3sW(  # noqa: N802
    request: FixtureRequest, duplex_apartment: file
) -> None:
    tree = initialize_tree(duplex_apartment)
    space = duplex_apartment.by_guid("0pNy6pOyf7JPmXRLgxs3sW")
    boundaries = SpaceBoundaries.from_space_entity(duplex_apartment, tree, space)

    if SHOW_FIGURES:
        boundaries.show()

    assert compare(boundaries, request)


def test_intersection_space_iinternal_wall_0pNy6pOyf7JPmXRLgxs3sW(  # noqa: N802
    request: FixtureRequest, duplex_apartment: file
) -> None:
    space = duplex_apartment.by_guid("0pNy6pOyf7JPmXRLgxs3sW")
    door = duplex_apartment.by_guid("2O2Fr$t4X7Zf8NOew3FLPP")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)

    assert intersection is None


def test_intersection_space_internal_wall(
    request: FixtureRequest, duplex_apartment: file
) -> None:
    space_1 = duplex_apartment.by_guid("10mjSDZJj9gPS2PrQaxa4o")
    space_2 = duplex_apartment.by_guid("0pNy6pOyf7JPmXRLgxs3sW")
    tree = initialize_tree(duplex_apartment)
    space_1_boundaries = SpaceBoundaries.from_space_entity(
        duplex_apartment, tree, space_1
    )
    space_2_boundaries = SpaceBoundaries.from_space_entity(
        duplex_apartment, tree, space_2
    )
    internal_elements = get_internal_elements([space_1_boundaries, space_2_boundaries])
    assert len(internal_elements.elements) == 1


def test_intersection_another_space_window(
    request: FixtureRequest, duplex_apartment: file
) -> None:
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_apartment.by_guid("1hOSvn6df7F8_7GcBWlSXO")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_intersection_another_space_small_window(
    request: FixtureRequest, duplex_apartment: file
) -> None:
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_apartment.by_guid("1hOSvn6df7F8_7GcBWlSnC")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)

    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_get_space_boundaries_two_zones(
    request: FixtureRequest, two_zones: file
) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_space_paramaters(two_zones: file) -> None:
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    space_ = Space.from_entity(space)
    assert space_.check_volume()


def test_space_paramaters_another(duplex_apartment: file) -> None:
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    space_ = Space.from_entity(space)
    assert not space_.check_volume()  # TODO: why?


def test_space_paramaters_another_space(duplex_apartment: file) -> None:
    space = duplex_apartment.by_guid("0BTBFw6f90Nfh9rP1dlXri")
    space_ = Space.from_entity(space)
    assert space_.check_volume()


def test_intersection_space_space(request: FixtureRequest, two_zones: file) -> None:
    space_1 = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    space_2 = two_zones.by_guid("3NzGTD1DeLJR3FlSqrXdUp")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_intersection_space_windows_multizone(
    request: FixtureRequest, multizone: file
) -> None:
    space_1 = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    space_2 = multizone.by_guid("1cMdolzEBzHfSYIkD4K2Kb")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_get_space_boundaries_multizone(
    request: FixtureRequest, multizone: file
) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_get_space_boundaries_two_zones_slab(two_zones: file) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    constructions = Constructions.from_ifc(two_zones)
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    trano_space = boundaries.model([], Vector(x=0, y=1, z=0), constructions)
    floor = next(e for e in trano_space.external_boundaries if e.tilt.value == "floor")
    roof = next(e for e in trano_space.external_boundaries if e.tilt.value == "ceiling")
    assert int(roof.surface) == 9
    assert int(floor.surface) == 9


def test_get_space_boundaries_two_zones_slab__(
    request: FixtureRequest, two_zones: file
) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_intersection_smiley_west__(request: FixtureRequest, smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    tree = initialize_tree(smiley_west)
    boundaries = SpaceBoundaries.from_space_entity(smiley_west, tree, space_1)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_intersection_smiley_west(request: FixtureRequest, smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    space_2 = smiley_west.by_guid("1QJW0EW_H4Vwf8W_jP6RTh")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)

    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_intersection_smiley_west_space_wall(smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    space_2 = smiley_west.by_guid("30ZXiOcMb5genQip_0pTMX")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert intersection is None


def test_intersection_smiley_west_space_keller(smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    space_2 = smiley_west.by_guid("1XaA5$O45DKQ9RoZVD5HbP")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert intersection is None


def test_intersection_smiley_west_space_keller2(smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    space_2 = smiley_west.by_guid("3t64EORJzEcPzciJueEwr2")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert intersection is None


def test_boundaries_smiley_west(request: FixtureRequest, smiley_west: file) -> None:
    tree = initialize_tree(smiley_west)
    space = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    boundaries = SpaceBoundaries.from_space_entity(smiley_west, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_boundaries_multi_zone(request: FixtureRequest, multizone: file) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("1bshZfpTvuHP22DqhSU$H1")
    space_ = multizone.by_guid("0JuRo7Utw1He5uTVScZaH1")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    boundaries_ = SpaceBoundaries.from_space_entity(multizone, tree, space_)
    internal_elements = get_internal_elements([boundaries, boundaries_])
    assert len(internal_elements.elements) == 2
    assert compare(boundaries, request)


def test_boundaries_multi_zone_internal(
    request: FixtureRequest, multizone: file
) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("0JuRo7Utw1He5uTVScZaH1")
    space_ = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    boundaries_ = SpaceBoundaries.from_space_entity(multizone, tree, space_)
    internal_elements = get_internal_elements([boundaries, boundaries_])
    assert len(internal_elements.elements) == 2
    assert compare(boundaries, request)


def test_intersection_multi_zone(request: FixtureRequest, multizone: file) -> None:
    space_1 = multizone.by_guid("1bshZfpTvuHP22DqhSU$H1")
    space_2 = multizone.by_guid("31piOLXIOhIvlWhb_0MB3v")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert compare(intersection, request)


def test_intersection_residential(
    request: FixtureRequest, residential_house: file
) -> None:
    space_1 = residential_house.by_guid("3$f2p7VyLB7eox67SA_zKE")
    space_2 = residential_house.by_guid("17JZcMFrf5tOftUTidA0d3")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)

    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_intersection_residential_2(
    request: FixtureRequest, residential_house: file
) -> None:
    space_1 = residential_house.by_guid("347jFE2yX7IhCEIALmupEH")
    space_2 = residential_house.by_guid("25fsbPyk15VvuXI$yNKenK")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert compare(intersection, request)


def test_space_boundary_residential(
    request: FixtureRequest, residential_house: file
) -> None:
    tree = initialize_tree(residential_house)
    space = residential_house.by_guid("347jFE2yX7IhCEIALmupEH")
    boundaries = SpaceBoundaries.from_space_entity(residential_house, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)


def test_space_boundary_layer(request: FixtureRequest, layer: file) -> None:

    tree = initialize_tree(layer)
    space = layer.by_guid("2sostWXevAUhKvlEHMOPJI")
    boundaries = SpaceBoundaries.from_space_entity(layer, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert compare(boundaries, request)
