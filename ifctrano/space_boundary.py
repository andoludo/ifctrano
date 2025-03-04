import multiprocessing
from typing import Optional, List, Tuple, Any

import ifcopenshell
from ifcopenshell import entity_instance
from pydantic import BaseModel, Field, ConfigDict
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifctrano.base import GlobalId, settings
from ifctrano.bounding_box import BoundingBox
from ifctrano.exceptions import NoIntersectionAreaFoundError


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
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: Optional[str] = None
    bounding_box: BoundingBox
    entity: entity_instance


# class BuildingElement(GlobalId):
#     element_type: str


class SpaceBoundary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    bounding_box: BoundingBox
    entity: entity_instance
    area: float

    @classmethod
    def from_space_and_element(
        cls, bounding_box: BoundingBox, element: entity_instance
    ) -> Optional["SpaceBoundary"]:
        bounding_box_ = BoundingBox.from_element(element)
        area = bounding_box.intersection_surface(bounding_box_).area
        if area:
            return cls(
                bounding_box=bounding_box_,
                entity=element,
                area=bounding_box.intersection_surface(bounding_box_).area,
            )
        return None

    def description(self) ->Tuple[float, Any, str]:
        return (self.area, self.entity.GlobalId, self.entity.is_a())


class SpaceBoundaries(BaseModel):
    space: Space
    boundaries: List[SpaceBoundary] = Field(default_factory=list)

    @classmethod
    def from_space_entity(
        cls, ifcopenshell_file, tree: ifcopenshell.geom.tree, space: entity_instance
    ):
        bounding_box = BoundingBox.from_element(space)
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
                space_boundary = SpaceBoundary.from_space_and_element(bounding_box, element)
                if space_boundary:
                    space_boundaries.append(space_boundary)
        return cls(space=space_, boundaries=space_boundaries)
