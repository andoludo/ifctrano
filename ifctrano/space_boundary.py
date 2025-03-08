import multiprocessing
import re
from typing import Optional, List, Tuple, Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell import entity_instance, file
from pydantic import BaseModel, Field
from trano.data_models.conversion import SpaceParameter  # type: ignore
from trano.elements import Space as TranoSpace, ExternalWall, Window, BaseWall  # type: ignore
from trano.elements.construction import Construction, Layer, Material  # type: ignore
from trano.elements.system import Occupancy  # type: ignore
from trano.elements.types import Azimuth, Tilt  # type: ignore

from ifctrano.base import (
    GlobalId,
    settings,
    BaseModelConfig,
    CommonSurface,
    ROUNDING_FACTOR,
)
from ifctrano.bounding_box import OrientedBoundingBox


def initialize_tree(ifc_file: file) -> ifcopenshell.geom.tree:
    tree = ifcopenshell.geom.tree()

    iterator = ifcopenshell.geom.iterator(
        settings, ifc_file, multiprocessing.cpu_count()
    )
    if iterator.initialize():  # type: ignore
        while True:
            tree.add_element(iterator.get())  # type: ignore
            if not iterator.next():  # type: ignore
                break
    return tree


def remove_non_alphanumeric(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()


class Space(GlobalId):
    name: Optional[str] = None
    bounding_box: OrientedBoundingBox
    entity: entity_instance
    average_room_height: float
    floor_area: float
    bounding_box_height: float
    bounding_box_volume: float

    @classmethod
    def from_entity(cls, entity: entity_instance) -> "Space":
        bounding_box = OrientedBoundingBox.from_entity(entity)
        entity_shape = ifcopenshell.geom.create_shape(settings, entity)
        area = ifcopenshell.util.shape.get_footprint_area(entity_shape.geometry)  # type: ignore
        volume = ifcopenshell.util.shape.get_volume(entity_shape.geometry)  # type: ignore
        if area:
            average_room_height = volume / area
        else:
            area = bounding_box.volume / bounding_box.height
            average_room_height = bounding_box.height
        return cls(
            global_id=entity.GlobalId,
            name=entity.Name,
            bounding_box=bounding_box,
            entity=entity,
            average_room_height=average_room_height,
            floor_area=area,
            bounding_box_height=bounding_box.height,
            bounding_box_volume=bounding_box.volume,
        )

    def check_volume(self) -> bool:
        return round(self.bounding_box_volume, ROUNDING_FACTOR) == round(
            self.floor_area * self.average_room_height, ROUNDING_FACTOR
        )

    def space_name(self) -> str:
        main_name = (
            remove_non_alphanumeric(self.name)
            if self.name
            else remove_non_alphanumeric(self.entity.GlobalId)
        )
        return f"space_{main_name}_{self.entity.GlobalId}"


material_1 = Material(
    name="material_1",
    thermal_conductivity=0.046,
    specific_heat_capacity=940,
    density=80,
)
construction = Construction(
    name="construction_4",
    layers=[
        Layer(material=material_1, thickness=0.18),
    ],
)


class SpaceBoundary(BaseModelConfig):
    bounding_box: OrientedBoundingBox
    entity: entity_instance
    common_surface: CommonSurface
    adjacent_spaces: List[Space] = Field(default_factory=list)

    def model_element(self, exclude_entities: List[str]) -> Optional[BaseWall]:
        if self.entity.GlobalId in exclude_entities:
            return None
        if "wall" in self.entity.is_a().lower():
            return ExternalWall(
                surface=self.common_surface.area,
                azimuth=Azimuth.south,
                tilt=Tilt.wall,
                construction=construction,
            )
        if "window" in self.entity.is_a().lower():
            return Window(
                surface=self.common_surface.area,
                azimuth=Azimuth.south,
                tilt=Tilt.wall,
                construction=construction,
            )
        if "roof" in self.entity.is_a().lower():
            return ExternalWall(
                surface=self.common_surface.area,
                azimuth=Azimuth.south,
                tilt=Tilt.ceiling,
                construction=construction,
            )

        return None

    @classmethod
    def from_space_and_element(
        cls, bounding_box: OrientedBoundingBox, entity: entity_instance
    ) -> Optional["SpaceBoundary"]:
        bounding_box_ = OrientedBoundingBox.from_entity(entity)
        common_surface = bounding_box.intersect_faces(bounding_box_)
        if common_surface:
            return cls(
                bounding_box=bounding_box_, entity=entity, common_surface=common_surface
            )
        return None

    def description(self) -> Tuple[float, Tuple[float, ...], Any, str]:
        return (
            self.common_surface.area,
            self.common_surface.orientation.to_tuple(),
            self.entity.GlobalId,
            self.entity.is_a(),
        )


class SpaceBoundaries(BaseModel):
    space: Space
    boundaries: List[SpaceBoundary] = Field(default_factory=list)

    def model(self, exclude_entities: List[str]) -> TranoSpace:
        return TranoSpace(
            name=self.space.space_name(),
            occupancy=Occupancy(),
            parameters=SpaceParameter(
                floor_area=self.space.floor_area,
                average_room_height=self.space.average_room_height,
            ),
            external_boundaries=[
                boundary.model_element(exclude_entities)
                for boundary in self.boundaries
                if boundary.model_element(exclude_entities)
            ],
        )

    @classmethod
    def from_space_entity(
        cls,
        ifcopenshell_file: file,
        tree: ifcopenshell.geom.tree,
        space: entity_instance,
    ) -> "SpaceBoundaries":
        space_ = Space.from_entity(space)
        clashes = tree.clash_clearance_many(
            [space],
            ifcopenshell_file.by_type("IfcWall")
            + ifcopenshell_file.by_type("IfcSlab")
            + ifcopenshell_file.by_type("IfcRoof")
            + ifcopenshell_file.by_type("IfcDoor")
            + ifcopenshell_file.by_type("IfcWindow"),
            clearance=0.1,
        )
        space_boundaries = []

        for clash in clashes:
            elements = [
                ifcopenshell_file.by_guid(clash.a.get_argument(0)),
                ifcopenshell_file.by_guid(clash.b.get_argument(0)),
            ]
            for element in elements:
                if element.GlobalId == space.GlobalId:
                    continue
                space_boundary = SpaceBoundary.from_space_and_element(
                    space_.bounding_box, element
                )
                if space_boundary:
                    space_boundaries.append(space_boundary)
        return cls(space=space_, boundaries=space_boundaries)
