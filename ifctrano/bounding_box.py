from logging import getLogger
from typing import List, Optional, Any, Tuple, cast

import ifcopenshell
import numpy as np
from ifcopenshell import entity_instance
import ifcopenshell.geom
import ifcopenshell.util.shape
from pydantic import (
    BaseModel,
    Field,
)
from shapely import Polygon  # type: ignore

from ifctrano.base import (
    Point,
    Vector,
    P,
    Sign,
    CoordinateSystem,
    Vertices,
    BaseModelConfig,
    settings,
    CommonSurface,
    AREA_TOLERANCE,
    ROUNDING_FACTOR,
)
from ifctrano.exceptions import BoundingBoxFaceError

logger = getLogger(__name__)


def get_normal(
    centroid: Point,
    difference: Point,
    face_signs: List[Sign],
    coordinate_system: CoordinateSystem,
) -> Vector:
    point_0 = centroid + difference.s(face_signs[0])
    point_1 = centroid + difference.s(face_signs[1])
    point_2 = centroid + difference.s(face_signs[2])
    vector_1 = coordinate_system.project((point_1 - point_0).to_array())
    vector_2 = coordinate_system.project((point_2 - point_0).to_array())
    array = (
        (Vector.from_array(vector_1) * Vector.from_array(vector_2)).norm().to_array()
    )
    return Vector.from_array(array)


class Polygon2D(BaseModelConfig):
    polygon: Polygon
    normal: Vector
    length: float


class BoundingBoxFace(BaseModelConfig):
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
    ) -> "BoundingBoxFace":
        if len(face_signs) != len(set(face_signs)):
            raise BoundingBoxFaceError("Face signs must be unique")
        normal = get_normal(centroid, difference, face_signs, coordinate_system)
        vertices_ = [(centroid + difference.s(s)).to_list() for s in face_signs]
        vertices_ = [*vertices_, vertices_[0]]
        vertices__ = [coordinate_system.project(v) for v in vertices_]
        vertices = Vertices.from_arrays(vertices__)

        return cls(
            vertices=vertices, normal=normal, coordinate_system=coordinate_system
        )

    def get_face_area(self) -> float:
        polygon_2d = self.get_2d_polygon(self.coordinate_system)
        return cast(float, round(polygon_2d.polygon.area, ROUNDING_FACTOR))

    def get_2d_polygon(self, coordinate_system: CoordinateSystem) -> Polygon2D:

        projected_vertices = coordinate_system.inverse(self.vertices.to_array())
        projected_normal_index = Vector.from_array(
            coordinate_system.inverse(self.normal.to_array())
        ).get_normal_index()
        polygon = Polygon(
            [
                [v_ for i, v_ in enumerate(v) if i != projected_normal_index]
                for v in projected_vertices.tolist()
            ]
        )

        return Polygon2D(
            polygon=polygon,
            normal=self.normal,
            length=projected_vertices.tolist()[0][projected_normal_index],
        )


class BoundingBoxFaces(BaseModel):
    faces: List[BoundingBoxFace]

    def description(self) -> List[tuple[Any, Tuple[float, float, float]]]:
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


class ExtendCommonSurface(CommonSurface):
    distance: float

    def to_common_surface(self) -> CommonSurface:
        return CommonSurface(area=self.area, orientation=self.orientation)


class OrientedBoundingBox(BaseModel):
    faces: BoundingBoxFaces
    centroid: Point
    area_tolerance: float = Field(default=AREA_TOLERANCE)
    volume: float
    height: float

    def intersect_faces(self, other: "OrientedBoundingBox") -> Optional[CommonSurface]:
        extend_surfaces = []
        for face in self.faces.faces:

            for other_face in other.faces.faces:
                vector = face.normal * other_face.normal
                if vector.is_a_zero():
                    polygon_1 = other_face.get_2d_polygon(face.coordinate_system)
                    polygon_2 = face.get_2d_polygon(face.coordinate_system)
                    intersection = polygon_2.polygon.intersection(polygon_1.polygon)
                    if intersection.area > self.area_tolerance:
                        distance = abs(polygon_1.length - polygon_2.length)
                        area = intersection.area
                        direction_vector = (other.centroid - self.centroid).norm()
                        orientation = direction_vector.project(face.normal).norm()
                        extend_surfaces.append(
                            ExtendCommonSurface(
                                distance=distance, area=area, orientation=orientation
                            )
                        )
        if extend_surfaces:
            if not all(
                e.orientation == extend_surfaces[0].orientation for e in extend_surfaces
            ):
                logger.warning("Different orientations found. taking the max area")
                max_area = max([e.area for e in extend_surfaces])
                extend_surfaces = [e for e in extend_surfaces if e.area == max_area]
            extend_surface = sorted(
                extend_surfaces, key=lambda x: x.distance, reverse=True
            )[-1]
            return extend_surface.to_common_surface()
        return None

    @classmethod
    def from_vertices(
        cls, vertices: np.ndarray[tuple[int, ...], np.dtype[np.float64]]
    ) -> "OrientedBoundingBox":
        vertices_np = np.array(vertices)
        points = np.asarray(vertices_np)
        cov = np.cov(points, y=None, rowvar=0, bias=0)  # type: ignore
        v, vect = np.linalg.eig(np.round(cov, ROUNDING_FACTOR))
        tvect = np.transpose(vect)
        points_r = np.dot(points, np.linalg.inv(tvect))

        co_min = np.min(points_r, axis=0)
        co_max = np.max(points_r, axis=0)

        xmin, xmax = co_min[0], co_max[0]
        ymin, ymax = co_min[1], co_max[1]
        zmin, zmax = co_min[2], co_max[2]

        x_len = xmax - xmin
        y_len = ymax - ymin
        z_len = zmax - zmin
        xdif = x_len * 0.5
        ydif = y_len * 0.5
        zdif = z_len * 0.5

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
        corners_ = np.dot(corners, tvect)
        dims = np.transpose(corners_)
        x_size = np.max(dims[0]) - np.min(dims[0])
        y_size = np.max(dims[1]) - np.min(dims[1])
        z_size = np.max(dims[2]) - np.min(dims[2])
        coordinate_system = CoordinateSystem.from_array(tvect)
        c = P(x=cx, y=cy, z=cz)
        d = P(x=xdif, y=ydif, z=zdif)
        faces = BoundingBoxFaces.build(c, d, coordinate_system)
        return cls(
            faces=faces,
            centroid=Point.from_array(coordinate_system.project(c.to_array())),
            volume=x_size * y_size * z_size,
            height=z_size,
        )

    @classmethod
    def from_entity(cls, entity: entity_instance) -> "OrientedBoundingBox":
        entity_shape = ifcopenshell.geom.create_shape(settings, entity)

        vertices = ifcopenshell.util.shape.get_shape_vertices(
            entity_shape, entity_shape.geometry  # type: ignore
        )
        return cls.from_vertices(vertices)
