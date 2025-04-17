from itertools import combinations
from logging import getLogger
from typing import List, Optional, Any, Tuple, cast

import ifcopenshell
import numpy as np
import open3d
from ifcopenshell import entity_instance
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell.ifcopenshell_wrapper import IfcEntityInstanceData
import ifcopenshell.util.placement
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)
from shapely import Polygon  # type: ignore
from shapely.constructive import centroid
from vedo import Line, show

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
    CLASH_CLEARANCE,
    FaceVertices, BaseShow,
)
from ifctrano.exceptions import BoundingBoxFaceError, VectorWithNansError
from scipy.spatial import ConvexHull

logger = getLogger(__name__)


# class Polygon2D(BaseModelConfig):
#     polygon: Polygon
#     normal: Vector
#     length: float


class BoundingBoxFace(BaseModelConfig):
    vertices: FaceVertices
    normal: Vector

    @classmethod
    def build(cls, vertices: Vertices) -> "BoundingBoxFace":
        face_vertices = vertices.to_face_vertices()

        return cls(vertices=face_vertices, normal=face_vertices.get_normal())

    #
    # def get_face_area(self) -> float:
    #     return self.polygon.area
    # def get_2d_polygon_projected(self) -> Polygon2D:
    #
    #     projected_vertices = self.vertices.to_array()
    #     projected_normal_index = self.normal.get_normal_index()
    #     polygon = Polygon(
    #         [
    #             [v_ for i, v_ in enumerate(v) if i != projected_normal_index]
    #             for v in projected_vertices.tolist()
    #         ]
    #     )
    #
    #     return Polygon2D(
    #         polygon=polygon,
    #         normal=self.normal,
    #         length=projected_vertices.tolist()[0][projected_normal_index],
    #     )
    #
    # def get_2d_polygon(self, coordinate_system: CoordinateSystem) -> Polygon2D:
    #
    #     projected_vertices = coordinate_system.inverse(self.vertices.to_array())
    #     projected_normal_index = Vector.from_array(
    #         coordinate_system.inverse(self.normal.to_array())
    #     ).get_normal_index()
    #     polygon = Polygon(
    #         [
    #             [v_ for i, v_ in enumerate(v) if i != projected_normal_index]
    #             for v in projected_vertices.tolist()
    #         ]
    #     )
    #
    #     return Polygon2D(
    #         polygon=polygon,
    #         normal=self.normal,
    #         length=projected_vertices.tolist()[0][projected_normal_index],
    #     )


class BoundingBoxFaces(BaseModel):
    faces: List[BoundingBoxFace]

    def description(self) -> List[tuple[Any, Tuple[float, float, float]]]:
        return sorted([(f.vertices.to_list(), f.normal.to_tuple()) for f in self.faces])

    @classmethod
    def build(cls, box_points) -> "BoundingBoxFaces":
        faces = [
            [0, 1, 6, 3],
            [2, 5, 4, 7],
            [0, 3, 5, 2],
            [1, 7, 4, 6],
            [0, 2, 7, 1],
            [3, 6, 4, 5],
        ]
        faces = [
            BoundingBoxFace.build(Vertices.from_arrays(np.array(box_points)[face]))
            for face in faces
        ]
        return cls(faces=faces)


class ExtendCommonSurface(CommonSurface):
    distance: float

    def to_common_surface(self) -> CommonSurface:
        return CommonSurface(
            area=self.area,
            orientation=self.orientation,
            main_vertices=self.main_vertices,
            common_vertices=self.common_vertices,
        )


class OrientedBoundingBox(BaseShow):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    faces: BoundingBoxFaces
    centroid: Point
    area_tolerance: float = Field(default=AREA_TOLERANCE)
    volume: float
    height: float
    entity: Optional[entity_instance] = None

    def lines(self) -> List[Line]:
        lines = []
        for f in self.faces.faces:
            face = f.vertices.to_list()
            combinations(face, 2)
            for a, b in combinations(face, 2):
                lines.append(Line(a, b))
        return lines



    def contained(self, poly_1: Polygon, poly_2: Polygon) -> bool:
        include_1_in_2 = poly_1.contains(poly_2)
        include_2_in_1 = poly_2.contains(poly_1)
        return include_2_in_1 or include_1_in_2

    def intersect_faces(self, other: "OrientedBoundingBox") -> Optional[CommonSurface]:
        extend_surfaces = []
        for face in self.faces.faces:

            for other_face in other.faces.faces:
                vector = face.normal * other_face.normal
                if vector.is_a_zero():
                    projected_face_1 = face.vertices.project(face.vertices)
                    projected_face_2 = face.vertices.project(other_face.vertices)
                    polygon_1 = projected_face_1.to_polygon()
                    polygon_2 = projected_face_2.to_polygon()
                    intersection = polygon_2.intersection(polygon_1)
                    if intersection.area > self.area_tolerance or self.contained(
                        polygon_1, polygon_2
                    ):
                        distance = projected_face_1.get_distance(projected_face_2)
                        area = intersection.area
                        try:
                            direction_vector = (other.centroid - self.centroid).norm()
                            orientation = direction_vector.project(face.normal).norm()
                        except VectorWithNansError as e:
                            logger.error(
                                "Orientation vector was not properly computed when computing the intersection between "
                                f"two elements ({(self.entity.GlobalId, self.entity.is_a(), self.entity.Name) if self.entity else None}, {(other.entity.GlobalId, other.entity.is_a(), other.entity.Name)if other.entity else None}). Error: {e}"
                            )
                            continue
                        extend_surfaces.append(
                            ExtendCommonSurface(
                                distance=distance,
                                area=area,
                                orientation=orientation,
                                main_vertices=face.vertices,
                                common_vertices=projected_face_1.common_vertices(
                                    intersection
                                ),
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
        else:
            logger.warning(
                "No common surfaces found between between "
                f"two elements ({(self.entity.GlobalId, self.entity.is_a(), self.entity.Name) if self.entity else None}, {(other.entity.GlobalId, other.entity.is_a(), other.entity.Name) if other.entity else None})."
            )
        return None

    @classmethod
    def from_vertices(
        cls,
        vertices: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
        entity: Optional[entity_instance] = None,
    ) -> "OrientedBoundingBox":
        points_ = open3d.utility.Vector3dVector(vertices)
        mobb = open3d.geometry.OrientedBoundingBox.create_from_points_minimal(points_)
        height = (mobb.get_max_bound() - mobb.get_min_bound())[
            2
        ]  # assuming that height is the z axis
        centroid = Point.from_array(mobb.get_center())
        faces = BoundingBoxFaces.build(np.array(mobb.get_box_points()))
        return cls(
            faces=faces,
            centroid=centroid,
            volume=mobb.volume(),
            height=height,
            entity=entity,
        )

    @classmethod
    def from_entity(cls, entity: entity_instance) -> "OrientedBoundingBox":
        entity_shape = ifcopenshell.geom.create_shape(settings, entity)
        vertices = ifcopenshell.util.shape.get_shape_vertices(
            entity_shape, entity_shape.geometry  # type: ignore
        )
        vertices_ = Vertices.from_arrays(vertices)
        if not vertices_.is_box_shaped():
            vertices_ = vertices_.get_bounding_box()
        return cls.from_vertices(vertices_.to_array(), entity)
