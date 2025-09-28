from itertools import combinations
from logging import getLogger
from typing import List, Optional, Any, Tuple

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement
import ifcopenshell.util.shape
import numpy as np
import open3d  # type: ignore
from ifcopenshell import entity_instance
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)
from scipy.spatial import ConvexHull, QhullError  # type: ignore
from vedo import Line  # type: ignore

from ifctrano.base import (
    Point,
    Vector,
    Vertices,
    BaseModelConfig,
    settings,
    CommonSurface,
    AREA_TOLERANCE,
    FaceVertices,
    BaseShow,
)
from ifctrano.exceptions import VectorWithNansError

logger = getLogger(__name__)


class BoundingBoxFace(BaseModelConfig):
    vertices: FaceVertices
    normal: Vector

    @classmethod
    def build(cls, vertices: Vertices) -> "BoundingBoxFace":
        face_vertices = vertices.to_face_vertices()

        return cls(vertices=face_vertices, normal=face_vertices.get_normal())


class BoundingBoxFaces(BaseModel):
    faces: List[BoundingBoxFace]

    def description(self) -> List[tuple[Any, Tuple[float, float, float]]]:
        return sorted([(f.vertices.to_list(), f.normal.to_tuple()) for f in self.faces])

    @classmethod
    def build(
        cls, box_points: np.ndarray[tuple[int, ...], np.dtype[np.float64]]
    ) -> "BoundingBoxFaces":
        faces = [
            [0, 1, 6, 3],
            [2, 5, 4, 7],
            [0, 3, 5, 2],
            [1, 7, 4, 6],
            [0, 2, 7, 1],
            [3, 6, 4, 5],
        ]
        faces_ = [
            BoundingBoxFace.build(Vertices.from_arrays(np.array(box_points)[face]))
            for face in faces
        ]
        return cls(faces=faces_)


class ExtendCommonSurface(CommonSurface):
    distance: float

    def to_common_surface(self) -> CommonSurface:
        return CommonSurface(
            area=self.area,
            orientation=self.orientation,
            main_vertices=self.main_vertices,
            common_vertices=self.common_vertices,
            polygon=self.polygon,
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
            for a, b in combinations(face, 2):
                lines.append(Line(a, b))
        return lines

    def intersect_faces(self, other: "OrientedBoundingBox") -> Optional[CommonSurface]:
        extend_surfaces = []
        for face in self.faces.faces:

            for other_face in other.faces.faces:
                vector = face.normal * other_face.normal
                if vector.is_null():
                    projected_face_1 = face.vertices.project(face.vertices)
                    projected_face_2 = face.vertices.project(other_face.vertices)
                    polygon_1 = projected_face_1.to_polygon()
                    polygon_2 = projected_face_2.to_polygon()
                    intersection = polygon_2.intersection(polygon_1)
                    if intersection.area > self.area_tolerance:
                        distance = projected_face_1.get_distance(projected_face_2)
                        area = intersection.area
                        try:
                            direction_vector = (
                                other.centroid - self.centroid
                            ).normalize()
                            orientation = direction_vector.project(
                                face.normal
                            ).normalize()
                        except VectorWithNansError as e:
                            logger.warning(
                                "Orientation vector was not properly computed when computing the intersection between "
                                f"two elements "
                                f"({(self.entity.GlobalId, self.entity.is_a(), self.entity.Name) if self.entity else None}"  # noqa: E501
                                f", {(other.entity.GlobalId, other.entity.is_a(), other.entity.Name)if other.entity else None}). Error: {e}"  # noqa: E501
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
                                polygon=intersection.wkt,
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
                f"two elements "
                f"({(self.entity.GlobalId, self.entity.is_a(), self.entity.Name) if self.entity else None}, "
                f"{(other.entity.GlobalId, other.entity.is_a(), other.entity.Name) if other.entity else None})."
            )
        return None

    @classmethod
    def from_vertices(
        cls,
        vertices: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
        entity: Optional[entity_instance] = None,
    ) -> "OrientedBoundingBox":
        points_ = open3d.utility.Vector3dVector(vertices)
        mobb = open3d.geometry.OrientedBoundingBox.create_from_points_minimal(
            points_, robust=True
        )
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
        vertices_ = Vertices.from_arrays(np.asarray(vertices))
        try:
            hull = ConvexHull(vertices_.to_array())
            vertices_ = Vertices.from_arrays(vertices_.to_array()[hull.vertices])

        except QhullError:
            logger.error(
                f"Convex hull failed for {entity.GlobalId} ({entity.is_a()}).... Continuing without it."
            )
        points_ = open3d.utility.Vector3dVector(vertices_.to_array())
        aab = open3d.geometry.AxisAlignedBoundingBox.create_from_points(points_)
        return cls.from_vertices(aab.get_box_points(), entity)
