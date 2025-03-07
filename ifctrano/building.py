from pathlib import Path
from typing import List

import ifcopenshell
from ifcopenshell import file, entity_instance
from pydantic import validate_call
from trano.elements.library.library import Library  # type: ignore

from trano.topology import Network  # type: ignore

from ifctrano.base import BaseModelConfig, Libraries
from ifctrano.exceptions import IfcFileNotFoundError
from ifctrano.space_boundary import SpaceBoundaries, initialize_tree


def get_spaces(ifcopenshell_file: file) -> List[entity_instance]:
    return ifcopenshell_file.by_type("IfcSpace")


class Building(BaseModelConfig):
    name: str
    space_boundaries: List[SpaceBoundaries]
    ifc_file: file
    parent_folder: Path

    @classmethod
    def from_ifc(cls, ifc_file_path: Path) -> "Building":
        if not ifc_file_path.exists():
            raise IfcFileNotFoundError(
                f"File specified {ifc_file_path} does not exist."
            )
        ifc_file = ifcopenshell.open(str(ifc_file_path))
        tree = initialize_tree(ifc_file)
        spaces = get_spaces(ifc_file)
        space_boundaries = [
            SpaceBoundaries.from_space_entity(ifc_file, tree, space) for space in spaces
        ]
        return cls(
            space_boundaries=space_boundaries,
            ifc_file=ifc_file,
            parent_folder=ifc_file_path.parent,
            name=ifc_file_path.stem,
        )

    @validate_call
    def create_model(self, library: Libraries = "Buildings") -> str:
        network = Network(name=self.name, library=Library.from_configuration(library))
        network.add_boiler_plate_spaces(
            [space_boundary.model() for space_boundary in self.space_boundaries]
        )
        return network.model()  # type: ignore

    def save_model(self, library: Libraries = "Buildings") -> None:
        model_ = self.create_model(library)
        Path(self.parent_folder.joinpath(f"{self.name}.mo")).write_text(model_)
