from pathlib import Path
from typing import List

import ifcopenshell
from ifcopenshell import file
from trano.topology import Network

from ifctrano.base import BaseModelConfig
from ifctrano.space_boundary import SpaceBoundaries, initialize_tree


def get_spaces(ifcopenshell_file) -> List[ifcopenshell.entity_instance]:
    return ifcopenshell_file.by_type("IfcSpace")


class Building(BaseModelConfig):
    name: str
    space_boundaries: List[SpaceBoundaries]
    ifc_file: file
    parent_folder: Path

    @classmethod
    def from_ifc(cls, ifc_file_path: Path):
        ifc_file = ifcopenshell.open(str(ifc_file_path))
        tree = initialize_tree(ifc_file)
        spaces = get_spaces(ifc_file)
        space_boundaries = []
        for space in spaces:
            space_boundaries.append(
                SpaceBoundaries.from_space_entity(ifc_file, tree, space)
            )

        return cls(
            space_boundaries=space_boundaries,
            ifc_file=ifc_file,
            parent_folder=ifc_file_path.parent,
            name=ifc_file_path.stem,
        )

    def write_model(self) -> None:
        network = Network(name=self.name)
        network.add_boiler_plate_spaces(
            [space_boundary.model() for space_boundary in self.space_boundaries]
        )
        model_ = network.model()
        Path(self.parent_folder.joinpath(f"{self.name}.mo")).write_text(model_)
