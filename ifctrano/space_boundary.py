import multiprocessing
import re
from typing import Optional, List, Tuple, Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell import entity_instance, file
from pydantic import BaseModel, Field
from trano.elements import Space as TranoSpace, ExternalWall, Window, BaseWall  # type: ignore
from trano.elements.construction import Construction, Layer, Material  # type: ignore
from trano.elements.system import Occupancy  # type: ignore
from trano.elements.types import Azimuth, Tilt  # type: ignore

from ifctrano.base import GlobalId, settings, BaseModelConfig, CommonSurface
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
    adjacent_space: Optional[Space] = None

    def model_element(self) -> Optional[BaseWall]:
        if "wall" in self.entity.is_a().lower():
            return ExternalWall(
                surface=6.44,
                azimuth=Azimuth.south,
                tilt=Tilt.wall,
                construction=construction,
            )
        if "window" in self.entity.is_a().lower():
            return Window(
                surface=6.44,
                azimuth=Azimuth.south,
                tilt=Tilt.wall,
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

    def model(self) -> TranoSpace:
        return TranoSpace(
            name=self.space.space_name(),
            occupancy=Occupancy(),
            external_boundaries=[
                boundary.model_element()
                for boundary in self.boundaries
                if boundary.model_element()
            ],
        )

    @classmethod
    def from_space_entity(
        cls,
        ifcopenshell_file: file,
        tree: ifcopenshell.geom.tree,
        space: entity_instance,
    ) -> "SpaceBoundaries":
        bounding_box = OrientedBoundingBox.from_entity(space)
        space_ = Space(
            global_id=space.GlobalId,
            name=space.Name,
            bounding_box=bounding_box,
            entity=space,
        )
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
                    bounding_box, element
                )
                if space_boundary:
                    space_boundaries.append(space_boundary)
        return cls(space=space_, boundaries=space_boundaries)
