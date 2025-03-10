import re
from pathlib import Path
from typing import List, Tuple, Any, Optional

import ifcopenshell
from ifcopenshell import file, entity_instance
from pydantic import validate_call, Field, model_validator, field_validator
from trano.elements import InternalElement  # type: ignore
from trano.elements.library.library import Library  # type: ignore
from trano.elements.types import Tilt  # type: ignore
from trano.topology import Network  # type: ignore

from ifctrano.base import BaseModelConfig, Libraries, Vector
from ifctrano.exceptions import IfcFileNotFoundError, NoIfcSpaceFoundError
from ifctrano.space_boundary import (
    SpaceBoundaries,
    initialize_tree,
    Space,
    construction,
)


def get_spaces(ifcopenshell_file: file) -> List[entity_instance]:
    return ifcopenshell_file.by_type("IfcSpace")


class IfcInternalElement(BaseModelConfig):
    spaces: List[Space]
    element: entity_instance
    area: float

    def __hash__(self) -> int:
        return hash(
            (
                *sorted([space.global_id for space in self.spaces]),
                self.element.GlobalId,
                self.area,
            )
        )

    def __eq__(self, other: "IfcInternalElement") -> bool:  # type: ignore
        return hash(self) == hash(other)

    def description(self) -> Tuple[Any, Any, str, float]:
        return (
            *sorted([space.global_id for space in self.spaces]),
            self.element.GlobalId,
            self.element.is_a(),
            self.area,
        )


class InternalElements(BaseModelConfig):
    elements: List[IfcInternalElement] = Field(default_factory=list)

    def internal_element_ids(self) -> List[str]:
        return list({e.element.GlobalId for e in self.elements})

    def description(self) -> List[Tuple[Any, Any, str, float]]:
        return sorted([element.description() for element in self.elements])


class Building(BaseModelConfig):
    name: str
    space_boundaries: List[SpaceBoundaries]
    ifc_file: file
    parent_folder: Path
    internal_elements: InternalElements = Field(default_factory=InternalElements)

    @field_validator("name")
    @classmethod
    def _name_validator(cls, name: str) -> str:
        name = name.replace(" ", "_")
        name = re.sub(r"[^a-zA-Z0-9_]", "", name)
        return name.lower()

    @classmethod
    def from_ifc(
        cls, ifc_file_path: Path, selected_spaces_global_id: Optional[List[str]] = None
    ) -> "Building":
        selected_spaces_global_id = selected_spaces_global_id or []
        if not ifc_file_path.exists():
            raise IfcFileNotFoundError(
                f"File specified {ifc_file_path} does not exist."
            )
        ifc_file = ifcopenshell.open(str(ifc_file_path))
        tree = initialize_tree(ifc_file)
        spaces = get_spaces(ifc_file)
        if selected_spaces_global_id:
            spaces = [
                space for space in spaces if space.GlobalId in selected_spaces_global_id
            ]
        if not spaces:
            raise NoIfcSpaceFoundError("No IfcSpace found in the file.")
        space_boundaries = [
            SpaceBoundaries.from_space_entity(ifc_file, tree, space) for space in spaces
        ]
        return cls(
            space_boundaries=space_boundaries,
            ifc_file=ifc_file,
            parent_folder=ifc_file_path.parent,
            name=ifc_file_path.stem,
        )

    @model_validator(mode="after")
    def _validator(self) -> "Building":
        self.internal_elements = self.get_adjacency()
        return self

    def get_adjacency(self) -> InternalElements:
        elements = []
        for space_boundaries_ in self.space_boundaries:
            for space_boundaries__ in self.space_boundaries:
                space_1 = space_boundaries_.space
                space_2 = space_boundaries__.space
                if space_1.global_id == space_2.global_id:
                    continue
                common_surface = space_1.bounding_box.intersect_faces(
                    space_2.bounding_box
                )
                for boundary in space_boundaries_.boundaries:
                    for boundary_ in space_boundaries__.boundaries:
                        if (
                            boundary.entity.GlobalId == boundary_.entity.GlobalId
                            and boundary.common_surface
                            and boundary_.common_surface
                            and common_surface
                            and (
                                boundary.common_surface.orientation
                                * common_surface.orientation
                            ).is_a_zero()
                            and (
                                boundary_.common_surface.orientation
                                * common_surface.orientation
                            ).is_a_zero()
                        ) and boundary.common_surface.orientation.dot(
                            boundary_.common_surface.orientation
                        ) < 0:
                            elements.append(  # noqa: PERF401
                                IfcInternalElement(
                                    spaces=[space_1, space_2],
                                    element=boundary_.entity,
                                    area=min(
                                        common_surface.area,
                                        boundary.common_surface.area,
                                        boundary_.common_surface.area,
                                    ),
                                )
                            )
        return InternalElements(elements=list(set(elements)))

    @validate_call
    def create_model(
        self,
        library: Libraries = "Buildings",
        north_axis: Optional[Vector] = None,
    ) -> str:
        north_axis = north_axis or Vector(x=0, y=1, z=0)
        network = Network(name=self.name, library=Library.from_configuration(library))
        spaces = {
            space_boundary.space.global_id: space_boundary.model(
                self.internal_elements.internal_element_ids(), north_axis
            )
            for space_boundary in self.space_boundaries
        }
        spaces = {k: v for k, v in spaces.items() if v}
        network.add_boiler_plate_spaces(list(spaces.values()), create_internal=False)
        for internal_element in self.internal_elements.elements:
            space_1 = internal_element.spaces[0]
            space_2 = internal_element.spaces[1]
            network.connect_spaces(
                spaces[space_1.global_id],
                spaces[space_2.global_id],
                InternalElement(
                    azimuth=10,
                    construction=construction,
                    surface=internal_element.area,
                    tilt=Tilt.wall,
                ),
            )
        return network.model()  # type: ignore

    def save_model(self, library: Libraries = "Buildings") -> None:
        model_ = self.create_model(library)
        Path(self.parent_folder.joinpath(f"{self.name}.mo")).write_text(model_)
