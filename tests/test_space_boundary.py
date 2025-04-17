from itertools import pairwise, combinations

import numpy as np
import open3d
from ifcopenshell import file
from open3d.cuda.pybind.utility import Vector3dVector
from scipy.spatial import ConvexHull
from vedo import show

from ifctrano.base import Vector
from ifctrano.bounding_box import OrientedBoundingBox
from ifctrano.building import get_internal_elements
from ifctrano.space_boundary import initialize_tree, SpaceBoundaries, Space

SHOW_FIGURES=True

def test_intersection_space_door(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_appartment.by_guid("1s1jVhK8z0pgKYcr9jt781")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (2.28867, [0.0, 1.0, 0.0])


def test_intersection_space_iinternal_wall(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    door = duplex_appartment.by_guid("2O2Fr$t4X7Zf8NOew3FNld")
    space_bbox = OrientedBoundingBox.from_entity(space)
    door_bbox = OrientedBoundingBox.from_entity(door)
    intersection = space_bbox.intersect_faces(door_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (9.24772, [-1.0, 0.0, 0.0])


def test_get_space_boundaries(duplex_appartment: file) -> None:
    tree = initialize_tree(duplex_appartment)
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    boundaries = SpaceBoundaries.from_space_entity(duplex_appartment, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert sorted([b.description() for b in boundaries.boundaries]) == [(2.28867, (0.0, 1.0, 0.0), '1s1jVhK8z0pgKYcr9jt781', 'IfcDoor'), (7.29408, (0.0, -0.0, 1.0), '1hOSvn6df7F8_7GcBWlRqU', 'IfcSlab'), (9.24772, (-1.0, 0.0, 0.0), '2O2Fr$t4X7Zf8NOew3FNld', 'IfcWallStandardCase'), (11.7007, (0.0, 1.0, 0.0), '1hOSvn6df7F8_7GcBWlR72', 'IfcWindow'), (12.34492, (1.0, 0.0, 0.0), '2O2Fr$t4X7Zf8NOew3FNqI', 'IfcWallStandardCase'), (14.92592, (0.0, 1.0, 0.0), '2O2Fr$t4X7Zf8NOew3FNtn', 'IfcWallStandardCase'), (17.73536, (0.0, -0.0, 1.0), '1hOSvn6df7F8_7GcBWlRrM', 'IfcSlab'), (27.66009, (0.0, 0.0, -1.0), '2O2Fr$t4X7Zf8NOew3FK4F', 'IfcSlab'), (27.66009, (0.0, 0.0, -1.0), '2OBrcmyk58NupXoVOHUtgP', 'IfcSlab')]


def test_get_space_boundaries_another_space(duplex_appartment: file) -> None:
    tree = initialize_tree(duplex_appartment)
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    boundaries = SpaceBoundaries.from_space_entity(duplex_appartment, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert sorted([b.description() for b in boundaries.boundaries]) == [(0.44429, (0.0, 0.0, -1.0), '2O2Fr$t4X7Zf8NOew3FNld', 'IfcWallStandardCase'), (0.62162, (0.0, 1.0, 0.0), '1hOSvn6df7F8_7GcBWlSga', 'IfcWindow'), (0.62162, (0.0, 1.0, 0.0), '1hOSvn6df7F8_7GcBWlSnC', 'IfcWindow'), (0.62162, (0.0, 1.0, 0.0), '1hOSvn6df7F8_7GcBWlSp1', 'IfcWindow'), (1.0737, (1.0, 0.0, -0.0), '2O2Fr$t4X7Zf8NOew3FLIE', 'IfcWallStandardCase'), (1.12806, (0.0, 0.0, -1.0), '2OBrcmyk58NupXoVOHUt8s', 'IfcSlab'), (1.65, (-1.0, 0.0, 0.0), '1l0GAJtRTFv8$zmKJOH4ZZ', 'IfcWindow'), (2.12242, (0.0, -1.0, 0.0), '1hOSvn6df7F8_7GcBWlSFK', 'IfcDoor'), (4.17864, (0.0, -1.0, 0.0), '2O2Fr$t4X7Zf8NOew3FLMr', 'IfcWallStandardCase'), (5.39171, (0.0, -1.0, 0.0), '2O2Fr$t4X7Zf8NOew3FLTF', 'IfcWallStandardCase'), (6.748, (0.0, 1.0, 0.0), '1hOSvn6df7F8_7GcBWlSXO', 'IfcWindow'), (9.57035, (0.0, 1.0, 0.0), '2O2Fr$t4X7Zf8NOew3FLQD', 'IfcWallStandardCase'), (16.12867, (-1.0, 0.0, 0.0), '2O2Fr$t4X7Zf8NOew3FLPP', 'IfcWallStandardCase'), (16.12867, (1.0, 0.0, -0.0), '2O2Fr$t4X7Zf8NOew3FKau', 'IfcWall'), (23.17129, (0.0, 0.0, -1.0), '1hOSvn6df7F8_7GcBWlRqU', 'IfcSlab'), (23.17129, (0.0, 0.0, -1.0), '2OBrcmyk58NupXoVOHUtC0', 'IfcSlab'), (23.17129, (0.0, 0.0, 1.0), '3ThA22djr8AQQ9eQMA5s7I', 'IfcSlab')]


def test_intersection_another_space_window(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_appartment.by_guid("1hOSvn6df7F8_7GcBWlSXO")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (6.748, [0.0, 1.0, 0.0])


def test_intersection_another_space_small_window(duplex_appartment: file) -> None:
    space = duplex_appartment.by_guid("0BTBFw6f90Nfh9rP1dl_39")
    window = duplex_appartment.by_guid("1hOSvn6df7F8_7GcBWlSnC")
    space_bbox = OrientedBoundingBox.from_entity(space)
    window_bbox = OrientedBoundingBox.from_entity(window)
    intersection = space_bbox.intersect_faces(window_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (0.62162, [0.0, 1.0, 0.0])


def test_get_space_boundaries_two_zones(two_zones: file) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert sorted([b.description() for b in boundaries.boundaries]) == [(1.0, (0.0, -1.0, 0.0), '3_bV5rUcEqG8kASS9SeipQ', 'IfcWindow'), (2.0, (0.0, 1.0, 0.0), '0t6bnTN6rtIuKOrcjLzg0Z', 'IfcDoor'), (9.0, (-1.0, 0.0, 0.0), '0iF2lvyBzlJgGtYWNfuhrr', 'IfcWallStandardCase'), (9.0, (0.0, -1.0, 0.0), '1vV1tvb7ErHeOK_7Z$PfBe', 'IfcWallStandardCase'), (9.0, (0.0, 0.0, -1.0), '2wnKoR7TlMJAMsrOjFIt2k', 'IfcSlab'), (9.0, (0.0, -0.0, 1.0), '1GtdW14ne2HvZSwZg9DViT', 'IfcSlab'), (9.0, (0.0, 1.0, 0.0), '0JPvTpQNrcIf4SV9z30TQ6', 'IfcWallStandardCase'), (9.0, (1.0, 0.0, 0.0), '3PvpR$hKFlHuhmlmbygBig', 'IfcWallStandardCase')]


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
    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (9.0, [-0.0, 1.0, -0.0])


def test_intersection_space_windows_multizone(multizone: file) -> None:
    space_1 = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    space_2 = multizone.by_guid("1cMdolzEBzHfSYIkD4K2Kb")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (39.2, [-1.0, 0.0, 0.0])


def test_get_space_boundaries_multizone(multizone: file) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert sorted([b.description() for b in boundaries.boundaries]) == [(2.0, (0.0, -1.0, 0.0), '19B65EIi3EIh2tA$vM8ZgT', 'IfcDoor'), (2.0, (1.0, 0.0, 0.0), '0jryqJ3XdhIf5exNfKRiH5', 'IfcDoor'), (7.75, (0.0, 1.0, 0.0), '1X7PJ2zxFYJQJ7zr1nDhxn', 'IfcWindow'), (21.6, (0.0, -1.0, 0.0), '2Mx5O979lPJu$FydjHS6_e', 'IfcWallStandardCase'), (21.6, (0.0, 1.0, 0.0), '0gSvHU18p4HuqD4mS$gG8D', 'IfcWallStandardCase'), (39.2, (-1.0, 0.0, 0.0), '1cMdolzEBzHfSYIkD4K2Kb', 'IfcWindow'), (50.22, (-1.0, 0.0, 0.0), '1116XLLwKdJRZmM_rK_l4f', 'IfcWallStandardCase'), (50.22, (1.0, 0.0, 0.0), '0idtIsso1oHPkD7tQ4ezLe', 'IfcWallStandardCase'), (148.8, (0.0, 0.0, -1.0), '2f4B0EKma$Gf_OoOWMssbl', 'IfcSlab'), (148.8, (0.0, -0.0, 1.0), '1Hey_hGXaaIvKh948Y5lwS', 'IfcSlab')]


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


def test_get_space_boundaries_two_zones_slab__(two_zones: file) -> None:
    tree = initialize_tree(two_zones)
    space = two_zones.by_guid("0t8Y4TnjqtGRnTw6NPeuj9")
    boundaries = SpaceBoundaries.from_space_entity(two_zones, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert sorted([b.description() for b in boundaries.boundaries]) == [(1.0, (0.0, -1.0, 0.0), '3_bV5rUcEqG8kASS9SeipQ', 'IfcWindow'), (2.0, (0.0, 1.0, 0.0), '0t6bnTN6rtIuKOrcjLzg0Z', 'IfcDoor'), (9.0, (-1.0, 0.0, 0.0), '0iF2lvyBzlJgGtYWNfuhrr', 'IfcWallStandardCase'), (9.0, (0.0, -1.0, 0.0), '1vV1tvb7ErHeOK_7Z$PfBe', 'IfcWallStandardCase'), (9.0, (0.0, 0.0, -1.0), '2wnKoR7TlMJAMsrOjFIt2k', 'IfcSlab'), (9.0, (0.0, -0.0, 1.0), '1GtdW14ne2HvZSwZg9DViT', 'IfcSlab'), (9.0, (0.0, 1.0, 0.0), '0JPvTpQNrcIf4SV9z30TQ6', 'IfcWallStandardCase'), (9.0, (1.0, 0.0, 0.0), '3PvpR$hKFlHuhmlmbygBig', 'IfcWallStandardCase')]

def test_intersection_smiley_west__(smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    tree = initialize_tree(smiley_west)
    boundaries = SpaceBoundaries.from_space_entity(smiley_west, tree, space_1)
    if SHOW_FIGURES:
        boundaries.show()
    assert sorted([b.description() for b in boundaries.boundaries]) == [(2.626, (0.0, 1.0, 0.0), '24C5qr6SP3Qf$NmDp6tGw$', 'IfcDoor'), (2.951, (0.0, -1.0, 0.0), '3YG$rrZ454$h5hiT23v5Gf', 'IfcDoor'), (5.2272, (1.0, 0.0, -0.0), '2KsmoW_kvD88gId1jurAra', 'IfcWallStandardCase'), (5.4222, (-1.0, 0.0, 0.0), '0Zj0JnUDvBBetlJkqI2svJ', 'IfcWallStandardCase'), (5.4222, (-1.0, 0.0, 0.0), '1nZXtbi0TBZf2uZX9$HIcx', 'IfcWallStandardCase'), (7.51913, (0.0, -0.0, -1.0), '2GlvzXHc9FQuvZMq6ig4MR', 'IfcSlab'), (7.51913, (0.0, 0.0, 1.0), '3leGSW3W91i96NfKGjz0WI', 'IfcSlab'), (9.3743, (0.0, -1.0, 0.0), '15fWlafVHCUPAj_neFFViv', 'IfcWallStandardCase'), (9.3743, (0.0, 1.0, 0.0), '1QJW0EW_H4Vwf8W_jP6RTh', 'IfcWallStandardCase')]


def test_intersection_smiley_west(smiley_west: file) -> None:
    space_1 = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    space_2 = smiley_west.by_guid("1QJW0EW_H4Vwf8W_jP6RTh")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    intersection = space_1_bbox.intersect_faces(space_2_bbox)

    if SHOW_FIGURES:
        intersection.show()
    assert intersection.description() == (9.3743, [0.0, 1.0, 0.0])


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


def test_boundaries_smiley_west(smiley_west: file) -> None:
    tree = initialize_tree(smiley_west)
    space = smiley_west.by_guid("2m3q9noR993uEdVygJK11m")
    boundaries = SpaceBoundaries.from_space_entity(smiley_west, tree, space)
    if SHOW_FIGURES:
        boundaries.show()
    assert {b.entity.Name for b in boundaries.boundaries} == {'EG-A-01-3', 'EG-A-02-1', 'EG-A-02-4', 'EG-Boden-02', 'EG-Haustuer-02', 'EG-I-02-1', 'EG-I-02-2', 'EG-Tür-02-2', 'OG-1-Boden-02'}


def test_boundaries_multi_zone(multizone: file) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("1bshZfpTvuHP22DqhSU$H1")
    space_ = multizone.by_guid("0JuRo7Utw1He5uTVScZaH1")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    boundaries_ = SpaceBoundaries.from_space_entity(multizone, tree, space_)
    internal_elements = get_internal_elements([boundaries, boundaries_])
    assert len(internal_elements.elements) == 2

def test_boundaries_multi_zone_internal(multizone: file) -> None:
    tree = initialize_tree(multizone)
    space = multizone.by_guid("0JuRo7Utw1He5uTVScZaH1")
    space_ = multizone.by_guid("3iLI4eTzPsHe5kCfE8mHt4")
    boundaries = SpaceBoundaries.from_space_entity(multizone, tree, space)
    boundaries_ = SpaceBoundaries.from_space_entity(multizone, tree, space_)
    internal_elements = get_internal_elements([boundaries, boundaries_])
    assert len(internal_elements.elements) == 2

def test_intersection_multi_zone(multizone: file) -> None:
    space_1 = multizone.by_guid("1bshZfpTvuHP22DqhSU$H1")
    space_2 = multizone.by_guid("31piOLXIOhIvlWhb_0MB3v")
    space_1_bbox = OrientedBoundingBox.from_entity(space_1)
    space_2_bbox = OrientedBoundingBox.from_entity(space_2)
    show(*space_1_bbox.lines(), *space_2_bbox.lines(), axes=1)

    intersection = space_1_bbox.intersect_faces(space_2_bbox)
    assert intersection is None