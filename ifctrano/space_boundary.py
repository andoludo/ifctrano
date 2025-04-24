import multiprocessing
from typing import Optional, List, Tuple, Any, Annotated

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell import entity_instance, file
from pydantic import Field, BeforeValidator, BaseModel
from trano.data_models.conversion import SpaceParameter  # type: ignore
from trano.elements import Space as TranoSpace, ExternalWall, Window, BaseWall, ExternalDoor  # type: ignore
from trano.elements.system import Occupancy  # type: ignore
from trano.elements.types import Tilt  # type: ignore
from vedo import Line  # type: ignore

from ifctrano.base import (
    GlobalId,
    settings,
    BaseModelConfig,
    CommonSurface,
    CLASH_CLEARANCE,
    Vector,
    BaseShow,
)
from ifctrano.bounding_box import OrientedBoundingBox
from ifctrano.construction import glass, Constructions
from ifctrano.exceptions import HasWindowsWithoutWallsError
from ifctrano.utils import remove_non_alphanumeric, _round, get_building_elements

ROOF_VECTOR = Vector(x=0, y=0, z=1)


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


class Space(GlobalId):
    name: Optional[str] = None
    bounding_box: OrientedBoundingBox
    entity: entity_instance
    average_room_height: Annotated[float, BeforeValidator(_round)]
    floor_area: Annotated[float, BeforeValidator(_round)]
    bounding_box_height: Annotated[float, BeforeValidator(_round)]
    bounding_box_volume: Annotated[float, BeforeValidator(_round)]

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
        return round(self.bounding_box_volume) == round(
            self.floor_area * self.average_room_height
        )

    def space_name(self) -> str:
        main_name = f"{remove_non_alphanumeric(self.name)}_" if self.name else ""
        return f"space_{main_name}{remove_non_alphanumeric(self.entity.GlobalId)}"


class ExternalSpaceBoundaryGroup(BaseModelConfig):
    constructions: List[BaseWall]
    azimuth: float
    tilt: Tilt

    def __hash__(self) -> int:
        return hash((self.azimuth, self.tilt.value))

    def has_window(self) -> bool:
        return any(
            isinstance(construction, Window) for construction in self.constructions
        )

    def has_external_wall(self) -> bool:
        return any(
            isinstance(construction, ExternalWall)
            for construction in self.constructions
        )


class ExternalSpaceBoundaryGroups(BaseModelConfig):
    space_boundary_groups: List[ExternalSpaceBoundaryGroup] = Field(
        default_factory=list
    )

    @classmethod
    def from_external_boundaries(
        cls, external_boundaries: List[BaseWall]
    ) -> "ExternalSpaceBoundaryGroups":
        boundary_walls = [
            ex
            for ex in external_boundaries
            if isinstance(ex, (ExternalWall, Window)) and ex.tilt == Tilt.wall
        ]
        space_boundary_groups = list(
            {
                ExternalSpaceBoundaryGroup(
                    constructions=[
                        ex_
                        for ex_ in boundary_walls
                        if ex_.azimuth == ex.azimuth and ex_.tilt == ex.tilt
                    ],
                    azimuth=ex.azimuth,
                    tilt=ex.tilt,
                )
                for ex in boundary_walls
            }
        )
        return cls(space_boundary_groups=space_boundary_groups)

    def has_windows_without_wall(self) -> bool:
        return all(
            not (group.has_window() and not group.has_external_wall())
            for group in self.space_boundary_groups
        )


class Azimuths(BaseModel):
    north: List[float] = [0.0, 360]
    east: List[float] = [90.0]
    south: List[float] = [180.0]
    west: List[float] = [270.0]
    northeast: List[float] = [45.0]
    southeast: List[float] = [135.0]
    southwest: List[float] = [225.0]
    northwest: List[float] = [315.0]
    tolerance: float = 22.5

    def get_azimuth(self, value: float) -> float:
        fields = [field for field in self.model_fields if field not in ["tolerance"]]
        for field in fields:
            possibilities = getattr(self, field)
            for possibility in possibilities:
                if (
                    value >= possibility - self.tolerance
                    and value <= possibility + self.tolerance
                ):
                    return float(possibilities[0])
        raise ValueError(f"Value {value} is not within tolerance of any azimuths.")


class SpaceBoundary(BaseModelConfig):
    bounding_box: OrientedBoundingBox
    entity: entity_instance
    common_surface: CommonSurface
    adjacent_spaces: List[Space] = Field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.common_surface)

    def boundary_name(self) -> str:
        return f"{self.entity.is_a()}_{remove_non_alphanumeric(self.entity.GlobalId)}"

    def model_element(  # noqa: PLR0911
        self,
        exclude_entities: List[str],
        north_axis: Vector,
        constructions: Constructions,
    ) -> Optional[BaseWall]:
        if self.entity.GlobalId in exclude_entities:
            return None
        azimuth = self.common_surface.orientation.angle(north_axis)
        if "wall" in self.entity.is_a().lower():
            return ExternalWall(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=Azimuths().get_azimuth(azimuth),
                tilt=Tilt.wall,
                construction=constructions.get_construction(self.entity),
            )
        if "door" in self.entity.is_a().lower():
            return ExternalDoor(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=Azimuths().get_azimuth(azimuth),
                tilt=Tilt.wall,
                construction=constructions.get_construction(self.entity),
            )
        if "window" in self.entity.is_a().lower():
            return Window(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=Azimuths().get_azimuth(azimuth),
                tilt=Tilt.wall,
                construction=glass,
            )
        if "roof" in self.entity.is_a().lower():
            return ExternalWall(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=azimuth,
                tilt=Tilt.ceiling,
                construction=constructions.get_construction(self.entity),
            )
        if "slab" in self.entity.is_a().lower():
            orientation = self.common_surface.orientation.dot(ROOF_VECTOR)
            return ExternalWall(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=azimuth,
                tilt=Tilt.ceiling if orientation > 0 else Tilt.floor,
                construction=constructions.get_construction(self.entity),
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


class SpaceBoundaries(BaseShow):
    space: Space
    boundaries: List[SpaceBoundary] = Field(default_factory=list)

    def description(self) -> set[tuple[float, tuple[float, ...], Any, str]]:
        return {b.description() for b in self.boundaries}

    def lines(self) -> List[Line]:
        lines = []
        for boundary in self.boundaries:
            lines += boundary.common_surface.lines()
        return lines

    def remove(self, space_boundaries: List[SpaceBoundary]) -> None:
        for space_boundary in space_boundaries:
            if space_boundary in self.boundaries:
                self.boundaries.remove(space_boundary)

    def model(
        self,
        exclude_entities: List[str],
        north_axis: Vector,
        constructions: Constructions,
    ) -> Optional[TranoSpace]:
        external_boundaries = []
        for boundary in self.boundaries:
            boundary_model = boundary.model_element(
                exclude_entities, north_axis, constructions
            )
            if boundary_model:
                external_boundaries.append(boundary_model)

        external_space_boundaries_group = (
            ExternalSpaceBoundaryGroups.from_external_boundaries(external_boundaries)
        )
        if not external_space_boundaries_group.has_windows_without_wall():
            raise HasWindowsWithoutWallsError(
                f"Space {self.space.global_id} has a boundary that has a windows but without walls."
            )
        return TranoSpace(
            name=self.space.space_name(),
            occupancy=Occupancy(),
            parameters=SpaceParameter(
                floor_area=self.space.floor_area,
                average_room_height=self.space.average_room_height,
            ),
            external_boundaries=external_boundaries,
        )

    @classmethod
    def from_space_entity(
        cls,
        ifcopenshell_file: file,
        tree: ifcopenshell.geom.tree,
        space: entity_instance,
    ) -> "SpaceBoundaries":
        space_ = Space.from_entity(space)

        elements = get_building_elements(ifcopenshell_file)
        clashes = tree.clash_clearance_many(
            [space],
            elements,
            clearance=CLASH_CLEARANCE,
        )
        space_boundaries = []
        elements_ = {
            entity
            for c in clashes
            for entity in [
                ifcopenshell_file.by_guid(c.a.get_argument(0)),
                ifcopenshell_file.by_guid(c.b.get_argument(0)),
            ]
            if entity.is_a() not in ["IfcSpace"]
        }

        for element in list(elements_):
            space_boundary = SpaceBoundary.from_space_and_element(
                space_.bounding_box, element
            )
            if space_boundary:
                space_boundaries.append(space_boundary)
        return cls(space=space_, boundaries=space_boundaries)
