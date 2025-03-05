import multiprocessing
from pathlib import Path
from typing import Optional, List, Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
import ifcopenshell.util.shape
import numpy as np
from pydantic import BaseModel, Field

import ifctrano.base
from ifctrano.base import GlobalId

from ifctrano.bounding_box import BoundingBox
from ifctrano.space_boundary import get_spaces, initialize_tree, SpaceBoundaries
import ifcopenshell.util.geolocation

SPACE_BOUNDARY_IFC = Path(__file__).parent / "models" / "space_boundary"
settings = ifcopenshell.geom.settings()


class BuildingElement(GlobalId):
    element_type: str


class SpaceBoundary(BaseModel):
    area: float
    bounding_space: Optional[Any] = None
    building_element: BuildingElement

    @classmethod
    def from_ifc_space_space_boundary(
        cls, ifc_space_boundary
    ) -> Optional["SpaceBoundary"]:

        if ifc_space_boundary.RelatedBuildingElement and (
            not ifc_space_boundary.ConnectionGeometry.SurfaceOnRelatingElement.is_a()
            in ["IfcSurfaceOfLinearExtrusion"]
        ):
            building_element_shape = ifcopenshell.geom.create_shape(
                settings, ifc_space_boundary.RelatedBuildingElement
            )
            shape = ifcopenshell.geom.create_shape(
                settings, ifc_space_boundary.ConnectionGeometry.SurfaceOnRelatingElement
            )
            area = ifcopenshell.util.shape.get_area(shape)
            element_type = ifc_space_boundary.RelatedBuildingElement.is_a()
            bounding_space = None
            if ifc_space_boundary.RelatingSpace:
                bounding_space = SpaceId(
                    global_id=ifctrano.base.GlobalId,
                    name=ifc_space_boundary.RelatingSpace.Name,
                )
            print(
                f"{ifc_space_boundary.ConnectionGeometry.SurfaceOnRelatingElement.is_a()} {area} {element_type}"
            )
            return cls(
                area=area,
                building_element=BuildingElement(
                    global_id=ifctrano.base.GlobalId,
                    element_type=element_type,
                ),
                bounding_space=bounding_space,
            )
        return None


# class Space(BaseModel):
#     id: SpaceId
#     bounded_by: List[SpaceBoundary] = Field(default_factory=list)
#
#     @classmethod
#     def from_ifc_space(cls, ifc_space) -> "Space":
#         a = 12


def test_read_ifc_space_boundary() -> None:
    duplex_appartment = SPACE_BOUNDARY_IFC / "Duplex_A.ifc"
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment))
    spaces = ifcopenshell_file.by_type("IfcSpace")
    tree = ifcopenshell.geom.tree()
    settings = ifcopenshell.geom.settings()
    iterator = ifcopenshell.geom.iterator(
        settings, ifcopenshell_file, multiprocessing.cpu_count()
    )
    if iterator.initialize():
        while True:
            # Use triangulation to build a BVH tree
            tree.add_element(iterator.get())

            # Alternatively, use this code to build an unbalanced binary tree
            # tree.add_element(iterator.get_native())

            if not iterator.next():
                break
    clashes = tree.clash_clearance_many(
        [spaces[0]],  # e.g. from model.by_type("IfcWall")
        ifcopenshell_file.by_type(
            "IfcWall"
        ),  # Group b can be the same as group a if you want to clash within a single set
        clearance=0.1,  # Include results where faces merely touch but do not intersect
    )

    for clash in clashes:
        element1 = clash.a
        element2 = clash.b
        a_global_id = element1.get_argument(0)
        b_global_id = element2.get_argument(0)
        element_1_shape = ifcopenshell.geom.create_shape(
            settings, ifcopenshell_file.by_guid(a_global_id)
        )
        element_2_shape = ifcopenshell.geom.create_shape(
            settings, ifcopenshell_file.by_guid(b_global_id)
        )
        ifcopenshell.util.shape.get_bbox(
            ifcopenshell.util.shape.get_shape_vertices(
                element_1_shape, element_1_shape.geometry
            )
        )
        ifcopenshell.util.shape.get_bbox(
            ifcopenshell.util.shape.get_shape_vertices(
                element_2_shape, element_2_shape.geometry
            )
        )
        ifcopenshell.util.shape.get_bbox(
            ifcopenshell.util.shape.get_shape_vertices(
                element_2_shape, element_2_shape.geometry
            )
        )

        # P1 and P2 represents two possible arbitrary points where a collision is found.
        # P1 may or may not be equal to P2.
        p1 = list(clash.p1)
        p2 = list(clash.p2)
    # space_shape = ifcopenshell.geom.create_shape(
    #     settings, spaces[0]
    # )
    # origin = (0., 0., 0.)
    # direction = (1., 0., 0.)
    # tree = ifcopenshell.geom.tree()
    # settings = ifcopenshell.geom.settings()
    # iterator = ifcopenshell.geom.iterator(settings, ifcopenshell_file, multiprocessing.cpu_count())
    # if iterator.initialize():
    #     while True:
    #         # Use triangulation to build a BVH tree
    #         tree.add_element(iterator.get())
    #
    #         # Alternatively, use this code to build an unbalanced binary tree
    #         # tree.add_element(iterator.get_native())
    #
    #         if not iterator.next():
    #             break
    # # results = tree.select_ray(origin, direction, length=5.)
    # elements = tree.select_box(spaces[0], completely_within=False, extend=50.)
    # origin = (0., 0., 0.)
    # direction = (1., 0., 0.)
    # results = tree.select_ray(origin, direction)
    # a = 12
    # for space in spaces:
    #     for space_boundary in space.BoundedBy:
    #         SpaceBoundary.from_ifc_space_space_boundary(space_boundary)


def test_read_ifc_space_boundary_2() -> None:
    duplex_appartment = SPACE_BOUNDARY_IFC / "MultiZoneBuilding.ifc"
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment))
    spaces = ifcopenshell_file.by_type("IfcSpace")
    for space in spaces:
        for space_boundary in space.BoundedBy:
            SpaceBoundary.from_ifc_space_space_boundary(space_boundary)


def test_read_ifc_spaces() -> None:
    duplex_appartment = SPACE_BOUNDARY_IFC / "Duplex_A.ifc"
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment))
    space = ifcopenshell_file.by_type("IfcSpace")[1]
    Space.from_ifc_space(space)


def test_bounding_box_trano():
    bounding_box_1 = ((6.2, -17.383, 0.019), (8.383, -8.075, 2.6))
    bounding_box_2 = (
        (-1.77635684e-15, -1.78000000e01, 0.00000000e00),
        (8.383, -17.383, 3.1),
    )
    bb_1 = BoundingBox.from_coordinate(bounding_box_1)
    bb_2 = BoundingBox.from_coordinate(bounding_box_2)
    intersection_ = bb_1.intersection_surface(bb_2)
    assert intersection_.valid()


def test_get_space_boundaries():
    duplex_appartment = SPACE_BOUNDARY_IFC / "Duplex_A.ifc"
    ifcopenshell_file = ifcopenshell.open(str(duplex_appartment))
    ifcopenshell.util.geolocation.get_wcs(ifcopenshell_file)
    tree = initialize_tree(ifcopenshell_file)
    space = ifcopenshell_file.by_guid("0BTBFw6f90Nfh9rP1dl_CZ")
    boundaries = SpaceBoundaries.from_space_entity(ifcopenshell_file, tree, space)
    assert sorted([b.description() for b in boundaries.boundaries]) == [
        (0.01, "1hOSvn6df7F8_7GcBWlRLx", "IfcWindow"),
        (2.29, "1s1jVhK8z0pgKYcr9jt781", "IfcDoor"),
        (9.25, "2O2Fr$t4X7Zf8NOew3FNld", "IfcWallStandardCase"),
        (11.7, "1hOSvn6df7F8_7GcBWlR72", "IfcWindow"),
        (12.34, "2O2Fr$t4X7Zf8NOew3FNqI", "IfcWallStandardCase"),
        (14.93, "2O2Fr$t4X7Zf8NOew3FNtn", "IfcWallStandardCase"),
        (27.66, "2O2Fr$t4X7Zf8NOew3FK4F", "IfcSlab"),
        (27.66, "2OBrcmyk58NupXoVOHUtgP", "IfcSlab"),
    ]


from ifctrano.base import Point


def test_orientation_vector():
    point_1 = Point(x=0, y=0, z=0)
    point_2 = Point(x=1, y=0, z=0)
    point_3 = Point(x=0, y=1, z=0)
    centroid_1 = Point(x=10, y=10, z=1)
    centroid_2 = Point(x=1, y=1, z=0)
    vector_centroid = centroid_2 - centroid_1
    vector_1 = point_2 - point_1
    vector_2 = point_3 - point_1
    normal_vector = vector_1 * vector_2
    vector_direction = vector_centroid.project(normal_vector)
    assert all(vector_direction.to_array() == np.array([0, 0, -1]))
    #see: https://blender.stackexchange.com/questions/261049/how-to-get-an-objects-oriented-bounding-box-obb-using-script


def test_compute_obb():
    vertices = [
        [2.6, -0.417, 0.019],
        [2.6, -0.417, 2.6],
        [2.6, -5.2, 2.6],
        [2.6, -5.2, 0.019],
        [8.383, -5.2, 2.6],
        [8.383, -5.2, 0.019],
        [8.383, -0.417, 2.6],
        [8.383, -0.417, 0.019]
    ]

    # Convert to NumPy array
    vertices_np = np.array(vertices)
    points = np.asarray(vertices_np)
    means = np.mean(points, axis=1)

    cov = np.cov(points, y=None, rowvar=0, bias=1)

    v, vect = np.linalg.eig(cov)

    tvect = np.transpose(vect)
    points_r = np.dot(points, np.linalg.inv(tvect))

    co_min = np.min(points_r, axis=0)
    co_max = np.max(points_r, axis=0)

    xmin, xmax = co_min[0], co_max[0]
    ymin, ymax = co_min[1], co_max[1]
    zmin, zmax = co_min[2], co_max[2]

    xdif = (xmax - xmin) * 0.5
    ydif = (ymax - ymin) * 0.5
    zdif = (zmax - zmin) * 0.5

    cx = xmin + xdif
    cy = ymin + ydif
    cz = zmin + zdif

    corners = np.array([
        [cx - xdif, cy - ydif, cz - zdif],
        [cx - xdif, cy + ydif, cz - zdif],
        [cx - xdif, cy + ydif, cz + zdif],
        [cx - xdif, cy - ydif, cz + zdif],
        [cx + xdif, cy + ydif, cz + zdif],
        [cx + xdif, cy + ydif, cz - zdif],
        [cx + xdif, cy - ydif, cz + zdif],
        [cx + xdif, cy - ydif, cz - zdif],
    ])

    corners = np.dot(corners, tvect)
    center = np.dot([cx, cy, cz], tvect)