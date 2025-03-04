from typing import Tuple, Annotated

import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell import entity_instance
from pydantic import BaseModel, computed_field, model_validator, BeforeValidator
from shapely import Polygon
from shapely.lib import intersection

from ifctrano.base import Point, settings
from ifctrano.exceptions import NoIntersectionAreaFoundError
def round_two_decimals(value: float) -> float:
    return round(value, 2)

class BoundingBoxIntersectionSurface(BaseModel):
    x_surface: Annotated[float, BeforeValidator(round_two_decimals)]
    y_surface: Annotated[float, BeforeValidator(round_two_decimals)]
    z_surface: Annotated[float, BeforeValidator(round_two_decimals)]




    @computed_field
    def area(self) ->float:
        return max([self.x_surface, self.y_surface, self.z_surface])


class BoundingBox(BaseModel):
    min_corner: Point
    max_corner: Point
    centroid: Point

    @classmethod
    def from_element(cls, element: entity_instance):
        element_2_shape = ifcopenshell.geom.create_shape(
            settings, element
        )
        points = ifcopenshell.util.shape.get_bbox(
            ifcopenshell.util.shape.get_shape_vertices(
                element_2_shape, element_2_shape.geometry
            )
        )
        centroid = ifcopenshell.util.shape.get_element_bbox_centroid(

                element, element_2_shape.geometry

        )
        return cls.from_coordinate((*points,centroid))

    @classmethod
    def from_coordinate(
        cls, points: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]
    ):
        min_corner = Point.from_coordinate(points[0])
        max_corner = Point.from_coordinate(points[1])
        centroid = Point.from_coordinate(points[1])
        return cls(min_corner=min_corner, max_corner=max_corner, centroid=centroid)

    def intersection_surface(
        self, other: "BoundingBox"
    ) -> BoundingBoxIntersectionSurface:
        x_surface = intersection(self.x_face(), other.x_face()).area
        y_surface = intersection(self.y_face(), other.y_face()).area
        z_surface = intersection(self.z_face(), other.z_face()).area
        return BoundingBoxIntersectionSurface(
            x_surface=x_surface, y_surface=y_surface, z_surface=z_surface
        )

    def x_face(self) -> Polygon:
        lines = [
            (self.min_corner.y, self.min_corner.z),
            (self.max_corner.y, self.min_corner.z),
            (self.max_corner.y, self.max_corner.z),
            (self.min_corner.y, self.max_corner.z),
            (self.min_corner.y, self.min_corner.z),
        ]
        return Polygon(lines)

    def y_face(self) -> Polygon:
        lines = [
            (self.min_corner.x, self.min_corner.z),
            (self.max_corner.x, self.min_corner.z),
            (self.max_corner.x, self.max_corner.z),
            (self.min_corner.x, self.max_corner.z),
            (self.min_corner.x, self.min_corner.z),
        ]
        return Polygon(lines)

    def z_face(self) -> Polygon:
        lines = [
            (self.min_corner.x, self.min_corner.y),
            (self.max_corner.x, self.min_corner.y),
            (self.max_corner.x, self.max_corner.y),
            (self.min_corner.x, self.max_corner.y),
            (self.min_corner.x, self.min_corner.y),
        ]
        return Polygon(lines)
