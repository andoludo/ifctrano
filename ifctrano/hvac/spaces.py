"""Assign distribution elements to the spaces they serve.

MEP elements are normally contained in a storey, not in a space. The space is
taken from an explicit ``IfcRelContainedInSpatialStructure`` or
``IfcRelReferencedInSpatialStructure`` relation when the model provides one,
matched by GlobalId so it also works across federated discipline models.
Otherwise the element's location is tested against the footprint and height
of each space of the architecture model.
"""

import logging
from collections.abc import Sequence

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.shape
import ifcopenshell.util.unit
import numpy as np
from ifcopenshell import entity_instance
from shapely import Point, Polygon, unary_union  # type: ignore

from ifctrano.base import settings
from ifctrano.space_boundary import Space

logger = logging.getLogger(__name__)


def ifc_file_of(element: entity_instance) -> ifcopenshell.file:
    return element.file  # type: ignore[no-any-return]


LOCATION_TOLERANCE = 0.5  # m
MINIMUM_TRIANGLE_AREA = 1e-9


class SpaceFootprint:
    def __init__(self, space: Space) -> None:
        self.space = space
        shape = ifcopenshell.geom.create_shape(settings, space.entity)
        vertices = np.asarray(
            ifcopenshell.util.shape.get_shape_vertices(shape, shape.geometry)  # type: ignore
        )
        faces = np.asarray(ifcopenshell.util.shape.get_faces(shape.geometry))  # type: ignore
        triangles = [Polygon(vertices[face][:, :2]) for face in faces]
        self.polygon = unary_union(
            [t for t in triangles if t.area > MINIMUM_TRIANGLE_AREA]
        )
        self.z_min = float(vertices[:, 2].min())
        self.z_max = float(vertices[:, 2].max())

    def height_matches(self, z: float) -> bool:
        return self.z_min - LOCATION_TOLERANCE <= z <= self.z_max


def element_location(element: entity_instance) -> np.ndarray:  # type: ignore[type-arg]
    """Centre of the element geometry in metres, or its placement origin."""
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
        vertices = np.asarray(
            ifcopenshell.util.shape.get_shape_vertices(shape, shape.geometry)  # type: ignore
        )
        return (vertices.min(axis=0) + vertices.max(axis=0)) / 2  # type: ignore
    except Exception:
        scale = ifcopenshell.util.unit.calculate_unit_scale(ifc_file_of(element))
        matrix = ifcopenshell.util.placement.get_local_placement(
            element.ObjectPlacement
        )
        return np.asarray(matrix[:3, 3]) * scale


class SpaceLocator:
    def __init__(self, spaces: Sequence[Space]) -> None:
        self.spaces = {space.global_id: space for space in spaces}
        self._footprints: list[SpaceFootprint] | None = None

    @property
    def footprints(self) -> list[SpaceFootprint]:
        if self._footprints is None:
            self._footprints = []
            for space in self.spaces.values():
                try:
                    self._footprints.append(SpaceFootprint(space))
                except Exception as e:  # noqa: PERF203
                    logger.warning(f"No footprint for space {space.global_id}: {e}")
        return self._footprints

    def locate(self, element: entity_instance) -> Space | None:
        related = [
            ifcopenshell.util.element.get_container(element),
            *ifcopenshell.util.element.get_referenced_structures(element),
        ]
        for structure in related:
            if structure is not None and structure.GlobalId in self.spaces:
                return self.spaces[structure.GlobalId]
        return self._locate_geometrically(element)

    def _locate_geometrically(self, element: entity_instance) -> Space | None:
        x, y, z = element_location(element)
        point = Point(x, y)
        candidates = [f for f in self.footprints if f.height_matches(z)]
        inside = [f for f in candidates if f.polygon.contains(point)]
        if inside:
            return min(inside, key=lambda f: f.polygon.area).space
        nearby = [
            (f.polygon.distance(point), f)
            for f in candidates
            if f.polygon.distance(point) <= LOCATION_TOLERANCE
        ]
        if nearby:
            return min(nearby, key=lambda item: item[0])[1].space
        return None
