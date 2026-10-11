import logging
import re
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple, Any, Optional, Set, Dict

import ifcopenshell
import yaml
from ifcopenshell import file, entity_instance
from pydantic import validate_call, Field, model_validator, field_validator
from trano.data_models.conversion import convert_network  # type: ignore
from trano.elements.library.library import Library  # type: ignore
from trano.elements.types import Tilt  # type: ignore
from trano.topology import Network  # type: ignore
from vedo import Line  # type: ignore

from ifctrano.base import BaseModelConfig, Libraries, Vector, BaseShow, CommonSurface
from ifctrano.exceptions import (
    IfcFileNotFoundError,
    NoIfcSpaceFoundError,
    NoSpaceBoundariesError,
)
from ifctrano.space_boundary import (
    SpaceBoundaries,
    initialize_tree,
    Space,
)
from ifctrano.construction import (
    Constructions,
    default_internal_construction,
)
from ifctrano.hvac import HeatingOptions, HeatingSystem, design_heat_load

logger = logging.getLogger(__name__)


def get_spaces(ifcopenshell_file: file) -> List[entity_instance]:
    return ifcopenshell_file.by_type("IfcSpace")


class IfcInternalElement(BaseModelConfig):
    spaces: List[Space]
    element: entity_instance
    area: float
    common_surface: CommonSurface

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

    def lines(self) -> List[Line]:
        lines = []
        if self.common_surface:
            lines += self.common_surface.lines()
        return lines


class InternalElements(BaseShow):
    elements: List[IfcInternalElement] = Field(default_factory=list)

    def internal_element_ids(self) -> List[str]:
        return list({e.element.GlobalId for e in self.elements})

    def description(self) -> Set[Tuple[Any, Any, str, float]]:
        return set(  # noqa: C414
            sorted([element.description() for element in self.elements])
        )


def get_internal_elements(space1_boundaries: List[SpaceBoundaries]) -> InternalElements:
    elements = []
    seen = set()
    common_boundaries = []
    for space_boundaries_ in space1_boundaries:
        for space_boundaries__ in space1_boundaries:
            space_1 = space_boundaries_.space
            space_2 = space_boundaries__.space

            if (
                space_1.global_id == space_2.global_id
                and (space_1.global_id, space_2.global_id) in seen
            ):
                continue
            seen.update(
                {
                    (space_1.global_id, space_2.global_id),
                    (space_2.global_id, space_1.global_id),
                }
            )
            common_surface = space_1.bounding_box.intersect_faces(space_2.bounding_box)

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
                        ).is_null()
                        and (
                            boundary_.common_surface.orientation
                            * common_surface.orientation
                        ).is_null()
                    ) and boundary.common_surface.orientation.dot(
                        boundary_.common_surface.orientation
                    ) < 0:
                        common_boundaries.extend([boundary, boundary_])
                        common_surface = sorted(
                            [boundary.common_surface, boundary_.common_surface],
                            key=lambda s: s.area,
                        )[0]
                        common_surface.exterior = False
                        elements.append(
                            IfcInternalElement(
                                spaces=[space_1, space_2],
                                element=boundary_.entity,
                                area=common_surface.area,
                                common_surface=common_surface,
                            )
                        )
    for space_boundaries_ in space1_boundaries:
        space_boundaries_.remove(common_boundaries)
    return InternalElements(elements=list(set(elements)))


class Building(BaseShow):
    name: str
    space_boundaries: List[SpaceBoundaries]
    ifc_file: file
    parent_folder: Path
    internal_elements: InternalElements = Field(default_factory=InternalElements)
    constructions: Constructions
    hvac_files: List[file] = Field(default_factory=list)
    heating: Optional[HeatingSystem] = None

    def get_boundaries(self, space_id: str) -> SpaceBoundaries:
        return next(
            sb for sb in self.space_boundaries if sb.space.global_id == space_id
        )

    def description(self) -> list[list[tuple[float, tuple[float, ...], Any, str]]]:
        return sorted([sorted(b.description()) for b in self.space_boundaries])

    def lines(self) -> List[Line]:
        lines = []
        for space_boundaries_ in [
            *self.space_boundaries,
            *self.internal_elements.elements,
        ]:
            lines += space_boundaries_.lines()  # type: ignore
        return lines

    @field_validator("name")
    @classmethod
    def _name_validator(cls, name: str) -> str:
        name = name.replace(" ", "_")
        name = re.sub(r"[^a-zA-Z0-9_]", "", name)
        return name.lower()

    @classmethod
    def from_ifc(
        cls,
        ifc_file_path: Path,
        selected_spaces_global_id: Optional[List[str]] = None,
        hvac_file_paths: Optional[Sequence[Path]] = None,
        heating_options: Optional[HeatingOptions] = None,
    ) -> "Building":
        """Building from an architecture IFC file.

        ``hvac_file_paths`` are optional federated discipline models (e.g. a
        heating model) sharing the coordinate system of the architecture model.
        Heating elements are also read from the architecture file itself.
        ``heating_options`` override the detected heat generator kind and set
        the design conditions used to size what the model does not specify.
        """
        selected_spaces_global_id = selected_spaces_global_id or []
        for path in [ifc_file_path, *(hvac_file_paths or [])]:
            if not path.exists():
                raise IfcFileNotFoundError(f"File specified {path} does not exist.")
        ifc_file = ifcopenshell.open(str(ifc_file_path))
        hvac_files = [ifcopenshell.open(str(path)) for path in hvac_file_paths or []]
        tree = initialize_tree(ifc_file)
        spaces = get_spaces(ifc_file)
        constructions = Constructions.from_ifc(ifc_file)
        if selected_spaces_global_id:
            spaces = [
                space for space in spaces if space.GlobalId in selected_spaces_global_id
            ]
        if not spaces:
            raise NoIfcSpaceFoundError("No IfcSpace found in the file.")
        space_boundaries = []
        for space in spaces:
            try:
                space_boundaries.append(
                    SpaceBoundaries.from_space_entity(ifc_file, tree, space)
                )
            except Exception as e:  # noqa: PERF203
                logger.error(f"Cannot process space {space.id()}. Reason {e}")
                continue
        if not space_boundaries:
            raise NoSpaceBoundariesError("No valid space boundaries found.")

        return cls(
            space_boundaries=space_boundaries,
            ifc_file=ifc_file,
            parent_folder=ifc_file_path.parent,
            name=ifc_file_path.stem,
            constructions=constructions,
            hvac_files=hvac_files,
            heating=HeatingSystem.from_ifc(
                [ifc_file, *hvac_files],
                [sb.space for sb in space_boundaries],
                heating_options,
            ),
        )

    @model_validator(mode="after")
    def _validator(self) -> "Building":
        self.internal_elements = self.get_adjacency()
        return self

    def get_adjacency(self) -> InternalElements:
        return get_internal_elements(self.space_boundaries)

    @validate_call
    def to_config(
        self,
        north_axis: Optional[Vector] = None,
    ) -> Dict[str, Any]:
        north_axis = north_axis or Vector(x=0, y=1, z=0)
        spaces = [
            space_boundary.to_config(
                self.internal_elements.internal_element_ids(),
                north_axis,
                self.constructions,
            )
            for space_boundary in self.space_boundaries
        ]
        spaces = [sp for sp in spaces if sp is not None]
        internal_walls = []

        for internal_element in self.internal_elements.elements:
            space_1 = internal_element.spaces[0]
            space_2 = internal_element.spaces[1]
            if any(
                name not in [sp["id"] for sp in spaces]  # type: ignore
                for name in [
                    space_1.space_unique_name(),
                    space_2.space_unique_name(),
                ]
            ):
                continue

            construction = self.constructions.get_construction(
                internal_element.element, default_internal_construction
            )
            if internal_element.element.is_a() in ["IfcSlab"]:
                space_1_tilt = (
                    Tilt.floor.value
                    if space_1.bounding_box.centroid.z > space_2.bounding_box.centroid.z
                    else Tilt.ceiling.value
                )
                space_2_tilt = (
                    Tilt.floor.value
                    if space_2.bounding_box.centroid.z > space_1.bounding_box.centroid.z
                    else Tilt.ceiling.value
                )
                if space_1_tilt == space_2_tilt:
                    logger.error("Space tilts are not compatible.")
                    continue
                internal_walls.append(
                    {
                        "space_1": space_1.space_unique_name(),
                        "space_2": space_2.space_unique_name(),
                        "construction": construction.name,
                        "surface": internal_element.area,
                        "space_1_tilt": space_1_tilt,
                        "space_2_tilt": space_2_tilt,
                    }
                )
            else:
                internal_walls.append(
                    {
                        "space_1": space_1.space_unique_name(),
                        "space_2": space_2.space_unique_name(),
                        "construction": construction.name,
                        "surface": internal_element.area,
                    }
                )
        construction_config = self.constructions.to_config()
        config = construction_config | {
            "spaces": spaces,
            "internal_walls": internal_walls,
        }
        if self.heating is not None:
            emissions, systems = self.heating.to_config(
                [sp["id"] for sp in spaces],  # type: ignore
                self.design_heat_loads(north_axis),
            )
            for space in spaces:
                if space["id"] in emissions:  # type: ignore
                    space["emissions"] = emissions[space["id"]]  # type: ignore
            if systems:
                config["systems"] = systems
        return config

    def design_heat_loads(self, north_axis: Vector) -> Dict[str, float]:
        """Design heat load (W) of each space, used to size heating components."""
        conditions = (
            self.heating.options.design
            if self.heating is not None
            else HeatingOptions().design
        )
        loads = {}
        for space_boundaries in self.space_boundaries:
            space = space_boundaries.model(
                self.internal_elements.internal_element_ids(),
                north_axis,
                self.constructions,
            )
            if space is not None:
                loads[space_boundaries.space.space_unique_name()] = design_heat_load(
                    space, conditions
                )
        return loads

    @validate_call
    def to_yaml(self, yaml_path: Path, north_axis: Optional[Vector] = None) -> None:
        config = self.to_config(north_axis=north_axis)
        yaml_data = yaml.dump(config)
        yaml_path.write_text(yaml_data)

    @validate_call
    def create_network(
        self,
        library: Libraries = "Buildings",
        north_axis: Optional[Vector] = None,
    ) -> Network:
        """trano network of the building, built from its configuration.

        Going through ``to_config`` keeps one translation of the building: the
        generated model is the one ``ifctrano config`` describes.
        """
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / f"{self.name}.yaml"
            self.to_yaml(config_path, north_axis=north_axis)
            return convert_network(
                self.name, config_path, library=Library.from_configuration(library)
            )

    def get_model(self) -> str:
        return str(self.create_network().model())

    def save_model(self, library: Libraries = "Buildings") -> None:
        model_ = self.create_network(library)
        Path(self.parent_folder.joinpath(f"{self.name}.mo")).write_text(model_.model())
