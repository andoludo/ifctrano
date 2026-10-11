import logging
import math
import multiprocessing
from typing import Optional, List, Tuple, Any, Annotated, Dict

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
from ifcopenshell import entity_instance, file
from pydantic import Field, BeforeValidator, BaseModel, ConfigDict
from shapely import wkt  # type: ignore
from trano.data_models.conversion import SpaceParameter  # type: ignore
from trano.elements import Space as TranoSpace, ExternalWall, Window, BaseWall, ExternalDoor  # type: ignore
from trano.elements.system import Occupancy  # type: ignore
from trano.elements.types import Azimuth, Tilt  # type: ignore
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
from ifctrano.construction import glass, Constructions, default_construction
from ifctrano.utils import (
    remove_non_alphanumeric,
    _round,
    get_building_elements,
    short_uuid,
)

ROOF_VECTOR = Vector(x=0, y=0, z=1)

logger = logging.getLogger(__name__)


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

    def space_unique_name(self) -> str:
        base_name = remove_non_alphanumeric(self.name) if self.name else ""
        main_name = f"{base_name}_" if base_name else ""
        space_name = f"{main_name}{remove_non_alphanumeric(self.entity.GlobalId)[-3:]}"
        if "space" not in space_name:
            return f"space_{space_name}"
        return space_name


MAX_WINDOW_TO_WALL_RATIO = 0.9
"""Window-to-wall ratio of a fully glazed facade, frames excluded."""


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

    def _merge(
        self,
        constructions: List[Window | ExternalWall],
        construction_type: type[Window | ExternalWall],
    ) -> List[Window | ExternalWall]:
        construction_types = [
            c for c in self.constructions if isinstance(c, construction_type)
        ]
        reference = next(iter(construction_types), None)
        if not reference:
            return []
        surface = sum([construction.surface for construction in construction_types])
        azimuth = reference.azimuth
        tilt = reference.tilt
        return [
            construction_type(
                surface=surface,
                azimuth=azimuth,
                tilt=tilt,
                construction=reference.construction,
            )
        ]

    def merge(self) -> None:
        self.constructions = [
            *self._merge(self.constructions, Window),
            *self._merge(self.constructions, ExternalWall),
        ]
        self._limit_window_area()

    def _limit_window_area(self) -> None:
        """Keep the windows within their wall, whose surface is the gross facade area.

        Windows larger than the wall of their orientation come from overlapping
        window bounding boxes, typically on glazed facades.
        """
        windows = [c for c in self.constructions if isinstance(c, Window)]
        walls = [c for c in self.constructions if isinstance(c, ExternalWall)]
        if not windows or not walls:
            return
        window_area = sum(window.surface for window in windows)
        wall_area = sum(wall.surface for wall in walls)
        if window_area <= wall_area:
            return
        limit = MAX_WINDOW_TO_WALL_RATIO * wall_area
        logger.warning(
            f"Windows of {window_area:.2f} m2 are larger than their wall of "
            f"{wall_area:.2f} m2 (azimuth {self.azimuth}): their area is reduced "
            f"to {limit:.2f} m2."
        )
        self.constructions = [
            (
                Window(
                    surface=c.surface * limit / window_area,
                    azimuth=c.azimuth,
                    tilt=c.tilt,
                    construction=c.construction,
                )
                if isinstance(c, Window)
                else c
            )
            for c in self.constructions
        ]

    def add_external_wall(self) -> None:
        reference = next(iter(self.constructions))
        surface = sum([construction.surface for construction in self.constructions]) * (
            0.7 / 0.3
        )
        azimuth = reference.azimuth
        tilt = reference.tilt
        self.constructions.append(
            ExternalWall(
                surface=surface,
                azimuth=azimuth,
                tilt=tilt,
                construction=default_construction,
            )
        )


class ExternalSpaceBoundaryGroups(BaseModelConfig):
    space_boundary_groups: List[ExternalSpaceBoundaryGroup] = Field(
        default_factory=list
    )
    remaining_constructions: List[BaseWall]

    @classmethod
    def from_external_boundaries(
        cls, external_boundaries: List[BaseWall]
    ) -> "ExternalSpaceBoundaryGroups":
        boundary_walls = [
            ex
            for ex in external_boundaries
            if isinstance(ex, (ExternalWall, Window)) and ex.tilt == Tilt.wall
        ]
        remaining_constructions = [
            ex
            for ex in external_boundaries
            if not (isinstance(ex, (ExternalWall, Window)) and ex.tilt == Tilt.wall)
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
        groups = cls(
            space_boundary_groups=space_boundary_groups,
            remaining_constructions=remaining_constructions,
        )
        groups.merge()
        return groups

    def has_windows_without_wall(self) -> bool:
        return all(
            not (group.has_window() and not group.has_external_wall())
            for group in self.space_boundary_groups
        )

    def add_external_walls(self) -> None:
        for group in self.space_boundary_groups:
            group.add_external_wall()

    def get_constructions(self) -> List[ExternalWall | Window]:
        return [
            *[c for group in self.space_boundary_groups for c in group.constructions],
            *self.remaining_constructions,
        ]

    def merge(self) -> None:
        for g in self.space_boundary_groups:
            g.merge()


AZIMUTH_DIGITS = 2
"""Azimuths are rounded like trano's ``Azimuth`` constants (1.57 for west)."""
HORIZONTAL_AZIMUTH = float(Azimuth.south)
"""Roofs and slabs: the azimuth of a horizontal surface does not change its physics."""


def bearing_to_azimuth(bearing: float) -> float:
    """Surface azimuth [rad] of an outward normal pointing to a compass ``bearing``.

    ``bearing`` is in degrees, clockwise from north (north 0, east 90, south 180,
    west 270), as returned by ``Vector.angle``. trano and the Modelica libraries
    use the azimuth of the Buildings library instead: radians from south,
    positive towards west (south 0, west pi/2, north pi, east -pi/2).
    """
    azimuth = math.remainder(math.radians(bearing - 180.0), 2 * math.pi)
    if math.isclose(azimuth, -math.pi):
        azimuth = math.pi
    return round(azimuth, AZIMUTH_DIGITS) + 0.0  # + 0.0 turns -0.0 into 0.0


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
        return (
            f"{remove_non_alphanumeric(self.entity.Name) or self.entity.is_a().lower()}_"
            f"__{remove_non_alphanumeric(self.entity.GlobalId)}{short_uuid()}"
        )

    def model_element(  # noqa: PLR0911
        self,
        exclude_entities: List[str],
        north_axis: Vector,
        constructions: Constructions,
    ) -> Optional[BaseWall]:
        if self.entity.GlobalId in exclude_entities:
            return None
        azimuth = bearing_to_azimuth(
            Azimuths().get_azimuth(self.common_surface.orientation.angle(north_axis))
        )
        if "wall" in self.entity.is_a().lower():
            return ExternalWall(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=azimuth,
                tilt=Tilt.wall,
                construction=constructions.get_construction(self.entity),
            )
        if "door" in self.entity.is_a().lower():
            return ExternalDoor(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=azimuth,
                tilt=Tilt.wall,
                construction=constructions.get_construction(self.entity),
            )
        if "window" in self.entity.is_a().lower():
            return Window(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=azimuth,
                tilt=Tilt.wall,
                construction=glass,
            )
        if "roof" in self.entity.is_a().lower():
            return ExternalWall(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=HORIZONTAL_AZIMUTH,
                tilt=Tilt.ceiling,
                construction=constructions.get_construction(self.entity),
            )
        if "slab" in self.entity.is_a().lower():
            orientation = self.common_surface.orientation.dot(ROOF_VECTOR)
            return ExternalWall(
                name=self.boundary_name(),
                surface=self.common_surface.area,
                azimuth=HORIZONTAL_AZIMUTH,
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

    def envelope(
        self,
        exclude_entities: List[str],
        north_axis: Vector,
        constructions: Constructions,
    ) -> Optional[List[BaseWall]]:
        """External envelope of the space, merged per orientation.

        Walls and windows of one orientation are merged, and a wall is added
        where the model has windows without walls.
        """
        boundaries = [
            model_element
            for boundary in self.boundaries
            if (
                model_element := boundary.model_element(
                    exclude_entities, north_axis, constructions
                )
            )
        ]
        if not boundaries:
            return None
        groups = ExternalSpaceBoundaryGroups.from_external_boundaries(boundaries)
        if not groups.has_windows_without_wall():
            groups.add_external_walls()
            logger.error(
                f"Space {self.space.global_id} has a boundary that has a windows but without walls."
            )
        return groups.get_constructions()

    def to_config(
        self,
        exclude_entities: List[str],
        north_axis: Vector,
        constructions: Constructions,
    ) -> Optional[Dict[str, Any]]:
        external_boundaries: Dict[str, Any] = {
            "external_walls": [],
            "floor_on_grounds": [],
            "windows": [],
        }
        envelope = self.envelope(exclude_entities, north_axis, constructions)
        if envelope is None:
            return None
        for boundary_model in envelope:
            element = {
                "surface": boundary_model.surface,
                "azimuth": boundary_model.azimuth,
                "tilt": boundary_model.tilt.value,
                "construction": boundary_model.construction.name,
            }
            if isinstance(
                boundary_model, (ExternalWall, ExternalDoor)
            ) and boundary_model.tilt in [Tilt.wall, Tilt.ceiling]:
                external_boundaries["external_walls"].append(element)
            elif isinstance(boundary_model, (Window)):
                external_boundaries["windows"].append(element)
            elif isinstance(boundary_model, (ExternalWall)) and boundary_model.tilt in [
                Tilt.floor
            ]:
                element.pop("azimuth")
                element.pop("tilt")
                external_boundaries["floor_on_grounds"].append(element)
            else:
                raise ValueError("Unknown boundary type")

        occupancy_parameters = Occupancy().parameters.model_dump(
            mode="json", exclude_none=True
        )
        space_parameters = SpaceParameter(
            floor_area=self.space.floor_area,
            average_room_height=self.space.average_room_height,
        ).model_dump(
            mode="json",
            exclude={"linearize_emissive_power", "volume"},
            exclude_none=True,
        )
        return {
            "id": self.space.space_unique_name(),
            "occupancy": {"parameters": occupancy_parameters},
            "parameters": space_parameters,
            "external_boundaries": external_boundaries,
        }

    def model(
        self,
        exclude_entities: List[str],
        north_axis: Vector,
        constructions: Constructions,
    ) -> Optional[TranoSpace]:
        envelope = self.envelope(exclude_entities, north_axis, constructions)
        if envelope is None:
            return None
        return TranoSpace(
            name=self.space.space_name(),
            occupancy=Occupancy(),
            parameters=SpaceParameter(
                floor_area=self.space.floor_area,
                average_room_height=self.space.average_room_height,
            ),
            external_boundaries=envelope,
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
        merged_boundaries = MergedSpaceBoundaries.from_boundaries(space_boundaries)
        space_boundaries_ = merged_boundaries.merge_boundaries_from_part()
        space_boundaries__ = remove_duplicate_boundaries(space_boundaries_)
        return cls(space=space_, boundaries=space_boundaries__)


def remove_duplicate_boundaries(
    boundaries: List[SpaceBoundary],
) -> List[SpaceBoundary]:
    types = ["IfcRoof", "IfcSlab"]
    boundaries = sorted(boundaries, key=lambda b: b.entity.GlobalId)
    boundaries_without_types = [
        sp for sp in boundaries if sp.entity.is_a() not in types
    ]
    new_boundaries = []
    for type_ in types:
        references = [sp for sp in boundaries if sp.entity.is_a() == type_]
        while True:
            reference = next(iter(references), None)
            if not reference:
                break
            others = [p_ for p_ in references if p_ != reference]
            intersecting = [
                o
                for o in others
                if (
                    wkt.loads(o.common_surface.polygon).intersects(
                        wkt.loads(reference.common_surface.polygon)
                    )
                    and o.common_surface.orientation
                    == reference.common_surface.orientation
                )
                and (
                    wkt.loads(o.common_surface.polygon).intersection(
                        wkt.loads(reference.common_surface.polygon)
                    )
                ).area
                > 0
            ]
            current_group = sorted(
                [*intersecting, reference], key=lambda p: p.entity.GlobalId
            )
            new_boundaries.append(next(iter(current_group)))
            references = [p_ for p_ in references if p_ not in current_group]
    return [*boundaries_without_types, *new_boundaries]


class MergedSpaceBoundary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    parent: entity_instance
    related_boundaries: List[SpaceBoundary]

    def get_new_boundary(self) -> Optional[SpaceBoundary]:
        related_boundaries = sorted(
            self.related_boundaries, key=lambda b: b.entity.GlobalId
        )
        boundary = next(iter(related_boundaries), None)
        if boundary:
            return SpaceBoundary.model_validate(
                boundary.model_dump() | {"entity": self.parent}
            )
        return None


class MergedSpaceBoundaries(BaseModel):
    part_boundaries: List[MergedSpaceBoundary]
    original_boundaries: List[SpaceBoundary]

    @classmethod
    def from_boundaries(
        cls, space_boundaries: List[SpaceBoundary]
    ) -> "MergedSpaceBoundaries":
        building_element_part_boundaries = [
            boundary
            for boundary in space_boundaries
            if boundary.entity.is_a() in ["IfcBuildingElementPart"]
        ]
        existing_parent_entities = {
            decompose.RelatingObject
            for b in building_element_part_boundaries
            for decompose in b.entity.Decomposes
        }
        part_boundaries = [
            MergedSpaceBoundary(
                parent=parent,
                related_boundaries=[
                    b
                    for b in building_element_part_boundaries
                    for decompose in b.entity.Decomposes
                    if decompose.RelatingObject == parent
                ],
            )
            for parent in existing_parent_entities
        ]
        return cls(
            part_boundaries=part_boundaries, original_boundaries=space_boundaries
        )

    def merge_boundaries_from_part(self) -> List[SpaceBoundary]:
        new_boundaries = [b.get_new_boundary() for b in self.part_boundaries]
        new_boundaries_ = [nb for nb in new_boundaries if nb is not None]
        return [
            b
            for b in self.original_boundaries
            if b.entity.is_a() not in ["IfcBuildingElementPart"]
        ] + new_boundaries_
