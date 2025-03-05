from typing import Tuple, Annotated, List, get_args

import ifcopenshell.geom
import ifcopenshell.util.shape
import numpy as np
from ifcopenshell import entity_instance
from pydantic import (
    BaseModel,
    computed_field,
    model_validator,
    BeforeValidator,
    ConfigDict,
)
from shapely import Polygon
from shapely.lib import intersection

from ifctrano.base import (
    Point,
    settings,
    Vector,
    Coordinate,
    P,
    Sign,
    CoordinateSystem,
    Vertices,
)
from ifctrano.exceptions import NoIntersectionAreaFoundError, BoundingBoxFaceError


def get_normal(
    centroid: Point,
    difference: Point,
    face_signs: List[Sign],
    coordinate_system: CoordinateSystem,
) -> Vector:
    point_0 = centroid + difference.s(face_signs[0])
    point_1 = centroid + difference.s(face_signs[1])
    point_2 = centroid + difference.s(face_signs[2])
    vector_1 = point_1 - point_0
    vector_2 = point_2 - point_0
    array = coordinate_system.project((vector_1 * vector_2).norm().to_array())
    return Vector.from_array(array)


class BoundingBoxFace(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    vertices: Vertices
    normal: Vector
    coordinate_system: CoordinateSystem

    @classmethod
    def build(
        cls,
        centroid: Point,
        difference: Point,
        face_signs: List[Sign],
        coordinate_system: CoordinateSystem,
    ):
        if len(face_signs) != len(set(face_signs)):
            raise BoundingBoxFaceError("Face signs must be unique")
        normal = get_normal(centroid, difference, face_signs, coordinate_system)
        vertices_ = [(centroid + difference.s(s)).to_list() for s in face_signs]
        vertices_ = vertices_ + [vertices_[0]]
        vertices__ = [coordinate_system.project(v) for v in vertices_]
        vertices = Vertices.from_arrays(vertices__)

        return cls(
            vertices=vertices, normal=normal, coordinate_system=coordinate_system
        )

    def get_2d_polygon(self, coordinate_system: CoordinateSystem) -> Polygon:
        projected_vertices = coordinate_system.inverse(self.vertices.to_array())
        projected_normal_index = Vector.from_array(
            coordinate_system.inverse(self.normal.to_array())
        ).get_normal_index()
        return Polygon(
            [
                [v_ for i, v_ in enumerate(v) if i != projected_normal_index]
                for v in projected_vertices.tolist()
            ]
        )


class BoundingBoxFaces(BaseModel):
    faces: List[BoundingBoxFace]

    def description(self):
        return sorted([(f.vertices.to_list(), f.normal.to_tuple()) for f in self.faces])

    @classmethod
    def build(
        cls, centroid: Point, difference: Point, coordinate_system: CoordinateSystem
    ) -> "BoundingBoxFaces":
        face_signs = [
            [Sign(x=-1, y=-1, z=-1), Sign(y=-1, z=-1), Sign(z=-1), Sign(x=-1, z=-1)],
            [Sign(x=-1, y=-1), Sign(y=-1), Sign(), Sign(x=-1)],
            [
                Sign(x=-1, y=-1, z=-1),
                Sign(x=-1, y=1, z=-1),
                Sign(x=-1, y=1, z=1),
                Sign(x=-1, y=-1, z=1),
            ],
            [
                Sign(x=1, y=-1, z=-1),
                Sign(x=1, y=1, z=-1),
                Sign(x=1, y=1, z=1),
                Sign(x=1, y=-1, z=1),
            ],
            [
                Sign(x=-1, y=-1, z=-1),
                Sign(x=1, y=-1, z=-1),
                Sign(x=1, y=-1, z=1),
                Sign(x=-1, y=-1, z=1),
            ],
            [
                Sign(x=-1, y=1, z=-1),
                Sign(x=1, y=1, z=-1),
                Sign(x=1, y=1, z=1),
                Sign(x=-1, y=1, z=1),
            ],
        ]
        faces = [
            BoundingBoxFace.build(centroid, difference, face_sign, coordinate_system)
            for face_sign in face_signs
        ]
        return cls(faces=faces)


class OrientedBoundingBox(BaseModel):
    faces: BoundingBoxFaces
    centroid: Point

    @classmethod
    def from_vertices(cls, vertices: List[List[float]]):
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
        corners = np.array(
            [
                [cx - xdif, cy - ydif, cz - zdif],
                [cx - xdif, cy + ydif, cz - zdif],
                [cx - xdif, cy + ydif, cz + zdif],
                [cx - xdif, cy - ydif, cz + zdif],
                [cx + xdif, cy + ydif, cz + zdif],
                [cx + xdif, cy + ydif, cz - zdif],
                [cx + xdif, cy - ydif, cz + zdif],
                [cx + xdif, cy - ydif, cz - zdif],
            ]
        )
        corners = np.dot(corners, tvect)
        # center = np.dot([cx, cy, cz], tvect)
        coordinate_system = CoordinateSystem.from_array(tvect)
        c = P(x=cx, y=cy, z=cz)
        d = P(x=xdif, y=ydif, z=zdif)
        faces = BoundingBoxFaces.build(c, d, coordinate_system)
        return cls(faces=faces, centroid=c)


#
#
# class BoundingBoxIntersectionSurface(BaseModel):
#     x_surface: Annotated[float, BeforeValidator(round_two_decimals)]
#     y_surface: Annotated[float, BeforeValidator(round_two_decimals)]
#     z_surface: Annotated[float, BeforeValidator(round_two_decimals)]
#
#     @computed_field
#     def area(self) -> float:
#         return max([self.x_surface, self.y_surface, self.z_surface])
#
#
#
#
#
#
#
# class BoundingBox(BaseModel):
#     min_corner: Point
#     max_corner: Point
#     centroid: Point
#     faces: List[BoundingBoxFace]
#
#     @classmethod
#     def from_element(cls, element: entity_instance):
#         element_2_shape = ifcopenshell.geom.create_shape(settings, element)
#         points = ifcopenshell.util.shape.get_bbox(
#             ifcopenshell.util.shape.get_shape_vertices(
#                 element_2_shape, element_2_shape.geometry
#             )
#         )
#         centroid = ifcopenshell.util.shape.get_element_bbox_centroid(
#             element, element_2_shape.geometry
#         )
#         return cls.from_coordinate((*points, centroid))
#
#     @classmethod
#     def from_coordinate(
#         cls,
#         points: Tuple[
#             Tuple[float, float, float],
#             Tuple[float, float, float],
#             Tuple[float, float, float],
#         ],
#     ):
#         min_corner = Point.from_coordinate(points[0])
#         max_corner = Point.from_coordinate(points[1])
#         centroid = Point.from_coordinate(points[1])
#         return cls(min_corner=min_corner, max_corner=max_corner, centroid=centroid)
#
#     def intersection_surface(
#         self, other: "BoundingBox"
#     ) -> BoundingBoxIntersectionSurface:
#         x_surface = intersection(self.x_face(), other.x_face()).area
#         y_surface = intersection(self.y_face(), other.y_face()).area
#         z_surface = intersection(self.z_face(), other.z_face()).area
#         return BoundingBoxIntersectionSurface(
#             x_surface=x_surface, y_surface=y_surface, z_surface=z_surface
#         )
#
#     def x_face(self) -> Polygon:
#         lines = [
#             (self.min_corner.y, self.min_corner.z),
#             (self.max_corner.y, self.min_corner.z),
#             (self.max_corner.y, self.max_corner.z),
#             (self.min_corner.y, self.max_corner.z),
#             (self.min_corner.y, self.min_corner.z),
#         ]
#         return Polygon(lines)
#
#     def y_face(self) -> Polygon:
#         lines = [
#             (self.min_corner.x, self.min_corner.z),
#             (self.max_corner.x, self.min_corner.z),
#             (self.max_corner.x, self.max_corner.z),
#             (self.min_corner.x, self.max_corner.z),
#             (self.min_corner.x, self.min_corner.z),
#         ]
#         return Polygon(lines)
#
#     def z_face(self) -> Polygon:
#         lines = [
#             (self.min_corner.x, self.min_corner.y),
#             (self.max_corner.x, self.min_corner.y),
#             (self.max_corner.x, self.max_corner.y),
#             (self.min_corner.x, self.max_corner.y),
#             (self.min_corner.x, self.min_corner.y),
#         ]
#         return Polygon(lines)
