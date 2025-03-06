import multiprocessing
from typing import Optional, List, Tuple, Any

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell import entity_instance
from pydantic import BaseModel, Field

from ifctrano.base import GlobalId, settings, BaseModelConfig, CommonSurface
from ifctrano.bounding_box import OrientedBoundingBox


def initialize_tree(ifcopenshell_file) -> ifcopenshell.geom.tree:

    tree = ifcopenshell.geom.tree()

    iterator = ifcopenshell.geom.iterator(
        settings, ifcopenshell_file, multiprocessing.cpu_count()
    )
    if iterator.initialize():
        while True:
            tree.add_element(iterator.get())
            if not iterator.next():
                break
    return tree


def get_spaces(ifcopenshell_file) -> List[ifcopenshell.entity_instance]:
    return ifcopenshell_file.by_type("IfcSpace")


class Space(GlobalId):
    name: Optional[str] = None
    bounding_box: OrientedBoundingBox
    entity: entity_instance


class SpaceBoundary(BaseModelConfig):
    bounding_box: OrientedBoundingBox
    entity: entity_instance
    common_surface: CommonSurface

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

    def description(self) -> Tuple[float, Tuple, Any, str]:
        return (
            self.common_surface.area,
            self.common_surface.orientation.to_tuple(),
            self.entity.GlobalId,
            self.entity.is_a(),
        )


class SpaceBoundaries(BaseModel):
    space: Space
    boundaries: List[SpaceBoundary] = Field(default_factory=list)

    @classmethod
    def from_space_entity(
        cls, ifcopenshell_file, tree: ifcopenshell.geom.tree, space: entity_instance
    ):
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
