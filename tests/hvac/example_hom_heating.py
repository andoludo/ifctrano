"""Generate a federated IFC4 heating discipline model for ``ExampleHOM.ifc``.

The heating model is a separate discipline file, as is common practice in
ISO 19650 federated BIM: it carries its own copy of the spatial structure
(project, site, building and storeys with the same GlobalIds and placements as
the architecture model) and only the heating elements.

The model follows IFC4 MEP conventions:

* specific classes and predefined types (IfcBoiler/WATER, IfcPump/CIRCULATOR,
  IfcValve/MIXING|REGULATING|ISOLATING, IfcSensor/TEMPERATURESENSOR,
  IfcSpaceHeater/RADIATOR, IfcPipeSegment, IfcPipeFitting);
* type objects carrying the standard property sets
  (Pset_BoilerTypeWater.HeatOutput, Pset_SpaceHeaterTypeCommon.OutputCapacity,
  Pset_PumpTypeCommon.FlowRateRange, ...);
* port-based connectivity (IfcDistributionPort nested with IfcRelNests,
  FlowDirection and SystemType set, linked with IfcRelConnectsPorts);
* supply and return IfcDistributionSystem (HEATING) per circuit, served to the
  building with IfcRelServicesBuildings;
* elements contained in their storey and referenced in the space they serve.

Two circuits (ground floor and first floor), each with a circulator, a mixing
valve and a flow temperature sensor, feed eleven radiators with thermostatic
valves. The living room has two radiators. The attic is unheated.

The output is deterministic: GlobalIds are derived from a fixed namespace and
the creation order, and the header timestamp is fixed.

Run ``python -m tests.hvac.example_hom_heating <output.ifc>`` to write the file.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.system
import ifcopenshell.api.type
import ifcopenshell.api.unit
import ifcopenshell.guid
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.shape  # must be imported before shape_builder
import ifcopenshell.util.shape_builder
import numpy as np

ARCHITECTURE_MODEL = (
    Path(__file__).parents[1] / "models" / "space_boundary" / "ExampleHOM.ifc"
)
GUID_NAMESPACE = uuid.UUID("6f0c3c55-6f0e-4b8e-9a43-2f1c7b0c9e11")
TIMESTAMP = "2026-01-01T00:00:00"

SUPPLY_TEMPERATURE = 343.15  # K, 70 °C design flow temperature
RETURN_TEMPERATURE = 328.15  # K, 55 °C design return temperature
PIPE_RADIUS = 0.011

Point = tuple[float, float, float]
Direction = Literal["SINK", "SOURCE"]


@dataclass(frozen=True)
class RadiatorType:
    name: str
    output_capacity: float  # W at 70/55/20 °C
    size: tuple[float, float, float]


PANEL_22_1000 = RadiatorType("Panel radiator 22 600x1000", 1680.0, (1.0, 0.1, 0.6))
PANEL_22_600 = RadiatorType("Panel radiator 22 600x600", 1010.0, (0.6, 0.1, 0.6))
PANEL_11_400 = RadiatorType("Panel radiator 11 600x400", 380.0, (0.4, 0.07, 0.6))


@dataclass(frozen=True)
class RadiatorSpec:
    space: str
    position: Point
    type: RadiatorType


@dataclass(frozen=True)
class CircuitSpec:
    name: str
    storey: str
    plant_position: Point
    radiators: Sequence[RadiatorSpec]


CIRCUITS = (
    CircuitSpec(
        name="GF",
        storey="GroundFloor",
        plant_position=(0.8, 3.2, 0.4),
        radiators=(
            RadiatorSpec("Living1", (1.2, 10.9, 0.15), PANEL_22_1000),
            RadiatorSpec("Living1", (3.2, 10.9, 0.15), PANEL_22_1000),
            RadiatorSpec("Kitchen5", (2.2, 0.45, 0.15), PANEL_22_600),
            RadiatorSpec("WC4", (6.3, 0.45, 0.15), PANEL_11_400),
            RadiatorSpec("Corridor3", (8.1, 5.7, 0.15), PANEL_11_400),
            RadiatorSpec("Hobby2", (6.3, 10.9, 0.15), PANEL_22_600),
        ),
    ),
    CircuitSpec(
        name="1F",
        storey="1stFloor",
        plant_position=(0.8, 2.4, 0.4),
        radiators=(
            RadiatorSpec("Bedroom6", (2.2, 10.9, 3.03), PANEL_22_1000),
            RadiatorSpec("Children10", (2.2, 0.45, 3.03), PANEL_22_600),
            RadiatorSpec("Bath9", (6.3, 0.45, 3.03), PANEL_22_600),
            RadiatorSpec("Corridor8", (8.1, 5.7, 3.03), PANEL_11_400),
            RadiatorSpec("Children7", (6.3, 10.9, 3.03), PANEL_22_600),
        ),
    ),
)
BOILER_POSITION: Point = (0.45, 4.0, 1.0)
BOILER_HEAT_OUTPUT = 18000.0  # W
PUMP_FLOW_RATE_MAX = 0.00025  # m3/s (0.9 m3/h)
PUMP_HEAD_MAX = 40000.0  # Pa


@dataclass
class Element:
    entity: ifcopenshell.entity_instance
    position: Point
    ports: dict[str, ifcopenshell.entity_instance] = field(default_factory=dict)


class HeatingModelBuilder:
    def __init__(self, architecture: ifcopenshell.file) -> None:
        self.architecture = architecture
        self.file = ifcopenshell.api.project.create_file(version="IFC4")
        self.file.wrapped_data.header.file_name.name = "ExampleHOM_heating.ifc"
        self.file.wrapped_data.header.file_name.time_stamp = TIMESTAMP
        self.file.wrapped_data.header.file_description.description = (
            "ViewDefinition [DesignTransferView]",
        )
        self._types: dict[tuple[str, str], ifcopenshell.entity_instance] = {}
        self._counter = 0
        self._create_project()

    # -- spatial structure -------------------------------------------------

    def _create_project(self) -> None:
        api = ifcopenshell.api
        arch_project = self.architecture.by_type("IfcProject")[0]
        self.project = self._mirror(arch_project)
        ifcopenshell.api.unit.assign_unit(
            self.file,
            units=[
                api.unit.add_si_unit(self.file, unit_type=unit_type)
                for unit_type in (
                    "LENGTHUNIT",
                    "AREAUNIT",
                    "VOLUMEUNIT",
                    "POWERUNIT",
                    "PRESSUREUNIT",
                    "THERMODYNAMICTEMPERATUREUNIT",
                )
            ],
        )
        model = api.context.add_context(self.file, context_type="Model")
        self.body = api.context.add_context(
            self.file,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=model,
        )
        site = self._mirror(self.architecture.by_type("IfcSite")[0], self.project)
        building = self._mirror(self.architecture.by_type("IfcBuilding")[0], site)
        self.building = building
        self.storeys = {
            storey.Name: self._mirror(storey, building)
            for storey in self.architecture.by_type("IfcBuildingStorey")
        }
        self.spaces = {
            space.Name: space for space in self.architecture.by_type("IfcSpace")
        }

    def _mirror(
        self,
        source: ifcopenshell.entity_instance,
        parent: ifcopenshell.entity_instance | None = None,
    ) -> ifcopenshell.entity_instance:
        """Copy a spatial element of the architecture model, keeping its GlobalId."""
        entity = ifcopenshell.api.root.create_entity(
            self.file, ifc_class=source.is_a(), name=source.Name
        )
        entity.GlobalId = source.GlobalId
        if source.is_a("IfcBuildingStorey"):
            entity.Elevation = source.Elevation
        if parent is not None:
            ifcopenshell.api.aggregate.assign_object(
                self.file, products=[entity], relating_object=parent
            )
        if getattr(source, "ObjectPlacement", None):
            ifcopenshell.api.geometry.edit_object_placement(
                self.file,
                product=entity,
                matrix=ifcopenshell.util.placement.get_local_placement(
                    source.ObjectPlacement
                ),
            )
        return entity

    # -- elements ----------------------------------------------------------

    def system(self, name: str) -> ifcopenshell.entity_instance:
        system = ifcopenshell.api.system.add_system(self.file)
        system.Name = name
        system.PredefinedType = "HEATING"
        system.ObjectType = None
        ifcopenshell.api.pset.edit_pset(
            self.file,
            pset=ifcopenshell.api.pset.add_pset(
                self.file, product=system, name="Pset_DistributionSystemCommon"
            ),
            properties={"Reference": name},
        )
        self.file.create_entity(
            "IfcRelServicesBuildings",
            GlobalId=ifcopenshell.guid.new(),
            RelatingSystem=system,
            RelatedBuildings=[self.building],
        )
        return system

    def element_type(
        self,
        ifc_class: str,
        name: str,
        predefined_type: str,
        psets: dict[str, dict[str, object]] | None = None,
    ) -> ifcopenshell.entity_instance:
        key = (ifc_class, name)
        if key not in self._types:
            type_ = ifcopenshell.api.root.create_entity(
                self.file,
                ifc_class=f"{ifc_class}Type",
                name=name,
                predefined_type=predefined_type,
            )
            for pset_name, properties in (psets or {}).items():
                self._add_pset(type_, pset_name, properties)
            self._types[key] = type_
        return self._types[key]

    def element(  # noqa: PLR0913
        self,
        ifc_class: str,
        *,
        name: str,
        type_: ifcopenshell.entity_instance | None,
        position: Point,
        storey: str,
        ports: dict[str, Direction],
        systems: Iterable[ifcopenshell.entity_instance],
        size: tuple[float, float, float] = (0.2, 0.2, 0.2),
        space: str | None = None,
    ) -> Element:
        self._counter += 1
        entity = ifcopenshell.api.root.create_entity(
            self.file, ifc_class=ifc_class, name=name
        )
        entity.Tag = f"{self._counter:03d}"
        if type_ is not None:
            ifcopenshell.api.type.assign_type(
                self.file, related_objects=[entity], relating_type=type_
            )
        self._place(entity, position)
        builder = ifcopenshell.util.shape_builder.ShapeBuilder(self.file)
        box = builder.block(
            position=(-size[0] / 2, -size[1] / 2, 0.0),
            x_length=size[0],
            y_length=size[1],
            z_length=size[2],
        )
        ifcopenshell.api.geometry.assign_representation(
            self.file,
            product=entity,
            representation=builder.get_representation(self.body, [box]),
        )
        ifcopenshell.api.spatial.assign_container(
            self.file, products=[entity], relating_structure=self.storeys[storey]
        )
        if space is not None:
            ifcopenshell.api.spatial.reference_structure(
                self.file, products=[entity], relating_structure=self._space(space)
            )
        for system in systems:
            ifcopenshell.api.system.assign_system(
                self.file, products=[entity], system=system
            )
        element = Element(entity=entity, position=position)
        for port_name, direction in ports.items():
            port = ifcopenshell.api.system.add_port(self.file, element=entity)
            port.Name = port_name
            port.FlowDirection = direction
            port.PredefinedType = "PIPE"
            port.SystemType = "HEATING"
            element.ports[port_name] = port
        return element

    def pipe(  # noqa: PLR0913
        self,
        source: ifcopenshell.entity_instance,
        target: ifcopenshell.entity_instance,
        start: Point,
        end: Point,
        storey: str,
        system: ifcopenshell.entity_instance,
    ) -> None:
        """Connect ``source`` (a SOURCE port) to ``target`` (a SINK port) with a pipe."""
        segment_type = self.element_type(
            "IfcPipeSegment",
            "Steel pipe DN15",
            "RIGIDSEGMENT",
            {"Pset_PipeSegmentTypeCommon": {"NominalDiameter": 0.015}},
        )
        self._counter += 1
        segment = ifcopenshell.api.root.create_entity(
            self.file, ifc_class="IfcPipeSegment", name=f"Pipe {self._counter:03d}"
        )
        ifcopenshell.api.type.assign_type(
            self.file, related_objects=[segment], relating_type=segment_type
        )
        self._place(segment, start)
        delta = np.subtract(end, start)
        if np.linalg.norm(delta) > 1e-6:
            builder = ifcopenshell.util.shape_builder.ShapeBuilder(self.file)
            solid = builder.create_swept_disk_solid(
                builder.polyline([(0.0, 0.0, 0.0), tuple(float(d) for d in delta)]),
                PIPE_RADIUS,
            )
            ifcopenshell.api.geometry.assign_representation(
                self.file,
                product=segment,
                representation=builder.get_representation(self.body, [solid]),
            )
        ifcopenshell.api.spatial.assign_container(
            self.file, products=[segment], relating_structure=self.storeys[storey]
        )
        ifcopenshell.api.system.assign_system(
            self.file, products=[segment], system=system
        )
        inlet = ifcopenshell.api.system.add_port(self.file, element=segment)
        outlet = ifcopenshell.api.system.add_port(self.file, element=segment)
        for port, direction in ((inlet, "SINK"), (outlet, "SOURCE")):
            port.PredefinedType = "PIPE"
            port.SystemType = "HEATING"
            port.FlowDirection = direction
        ifcopenshell.api.system.connect_port(self.file, source, inlet, "SOURCE")
        ifcopenshell.api.system.connect_port(self.file, outlet, target, "SOURCE")

    def tee(  # noqa: PLR0913
        self,
        name: str,
        position: Point,
        storey: str,
        system: ifcopenshell.entity_instance,
        *,
        diverging: bool,
    ) -> Element:
        type_ = self.element_type("IfcPipeFitting", "Tee DN15", "JUNCTION")
        ports: dict[str, Direction] = (
            {"in": "SINK", "out": "SOURCE", "branch": "SOURCE"}
            if diverging
            else {"in": "SINK", "branch": "SINK", "out": "SOURCE"}
        )
        return self.element(
            "IfcPipeFitting",
            name=name,
            type_=type_,
            position=position,
            storey=storey,
            ports=ports,
            systems=[system],
            size=(0.05, 0.05, 0.05),
        )

    # -- helpers -----------------------------------------------------------

    def _space(self, name: str) -> ifcopenshell.entity_instance:
        """Reference the architecture space by GlobalId (a stub in this file)."""
        arch_space = self.spaces[name]
        existing = [s for s in self.file.by_type("IfcSpace") if s.Name == name]
        if existing:
            return existing[0]
        space = ifcopenshell.api.root.create_entity(
            self.file, ifc_class="IfcSpace", name=name
        )
        space.GlobalId = arch_space.GlobalId
        storey = ifcopenshell.util.element.get_aggregate(arch_space)
        ifcopenshell.api.aggregate.assign_object(
            self.file, products=[space], relating_object=self.storeys[storey.Name]
        )
        ifcopenshell.api.geometry.edit_object_placement(
            self.file,
            product=space,
            matrix=ifcopenshell.util.placement.get_local_placement(
                arch_space.ObjectPlacement
            ),
        )
        return space

    def _place(self, entity: ifcopenshell.entity_instance, position: Point) -> None:
        matrix = np.eye(4)
        matrix[:3, 3] = position
        ifcopenshell.api.geometry.edit_object_placement(
            self.file, product=entity, matrix=matrix
        )

    def _add_pset(
        self,
        product: ifcopenshell.entity_instance,
        name: str,
        properties: dict[str, object],
    ) -> None:
        pset = ifcopenshell.api.pset.add_pset(self.file, product=product, name=name)
        simple = {k: v for k, v in properties.items() if not isinstance(v, tuple)}
        if simple:
            ifcopenshell.api.pset.edit_pset(self.file, pset=pset, properties=simple)
        for key, value in properties.items():
            if isinstance(value, tuple):  # (measure, lower, upper) bounded value
                measure, lower, upper = value
                pset.HasProperties = (
                    *(pset.HasProperties or ()),
                    self.file.create_entity(
                        "IfcPropertyBoundedValue",
                        Name=key,
                        LowerBoundValue=self.file.create_entity(measure, lower),
                        UpperBoundValue=self.file.create_entity(measure, upper),
                    ),
                )


def build(  # noqa: PLR0915
    architecture_path: Path = ARCHITECTURE_MODEL,
) -> ifcopenshell.file:
    builder = HeatingModelBuilder(ifcopenshell.open(str(architecture_path)))
    plant_storey = "GroundFloor"
    boiler = builder.element(
        "IfcBoiler",
        name="Gas condensing boiler",
        type_=builder.element_type(
            "IfcBoiler",
            "Gas condensing boiler 18 kW",
            "WATER",
            {
                "Pset_BoilerTypeCommon": {
                    "IsWaterStorageHeater": False,
                    "OutletTemperatureRange": (
                        "IfcThermodynamicTemperatureMeasure",
                        303.15,
                        353.15,
                    ),
                },
                "Pset_BoilerTypeWater": {
                    "HeatOutput": BOILER_HEAT_OUTPUT,
                    "NominalEfficiency": 0.95,
                },
            },
        ),
        position=BOILER_POSITION,
        storey=plant_storey,
        space="Kitchen5",
        ports={"return": "SINK", "flow": "SOURCE"},
        systems=[],
        size=(0.4, 0.35, 0.7),
    )
    isolating_type = builder.element_type(
        "IfcValve",
        "Ball valve DN20",
        "ISOLATING",
        {
            "Pset_ValveTypeCommon": {"WorkingPressure": 1000000.0},
            "Pset_ValveTypeIsolating": {"IsNormallyOpen": True},
        },
    )
    pump_type = builder.element_type(
        "IfcPump",
        "Circulator 25-40",
        "CIRCULATOR",
        {
            "Pset_PumpTypeCommon": {
                "FlowRateRange": (
                    "IfcVolumetricFlowRateMeasure",
                    0.0,
                    PUMP_FLOW_RATE_MAX,
                ),
                "FlowResistanceRange": ("IfcPressureMeasure", 0.0, PUMP_HEAD_MAX),
                "NominalRotationSpeed": 50.0,
            }
        },
    )
    mixing_type = builder.element_type(
        "IfcValve",
        "Three-way mixing valve DN20",
        "MIXING",
        {
            "Pset_ValveTypeCommon": {"FlowCoefficient": 4.0},
            "Pset_ValveTypeMixing": {"MixerControl": "MANUAL"},
        },
    )
    sensor_type = builder.element_type(
        "IfcSensor",
        "Flow temperature sensor",
        "TEMPERATURESENSOR",
        {"Pset_SensorTypeCommon": {"Reference": "PT1000 immersion sensor"}},
    )
    trv_type = builder.element_type(
        "IfcValve",
        "Thermostatic radiator valve DN15",
        "REGULATING",
        {"Pset_ValveTypeCommon": {"FlowCoefficient": 0.6}},
    )

    # Plant: boiler flow -> isolating valve -> flow header; return header ->
    # isolating valve -> boiler return.
    flow_iso = builder.element(
        "IfcValve",
        name="Isolating valve flow",
        type_=isolating_type,
        position=(0.45, 3.8, 0.6),
        storey=plant_storey,
        ports={"in": "SINK", "out": "SOURCE"},
        systems=[],
    )
    return_iso = builder.element(
        "IfcValve",
        name="Isolating valve return",
        type_=isolating_type,
        position=(0.55, 3.8, 0.6),
        storey=plant_storey,
        ports={"in": "SINK", "out": "SOURCE"},
        systems=[],
    )
    plant_systems = []
    flow_source = flow_iso.ports["out"]
    return_target = return_iso.ports["in"]
    flow_source_pos: Point = (0.45, 3.8, 0.6)
    return_target_pos: Point = (0.55, 3.8, 0.6)
    for index, circuit in enumerate(CIRCUITS):
        last = index == len(CIRCUITS) - 1
        supply = builder.system(f"Heating flow {circuit.name}")
        ret = builder.system(f"Heating return {circuit.name}")
        plant_systems += [supply, ret]
        x, y, z = circuit.plant_position
        # Header tee (or the end of the header for the last circuit).
        if not last:
            header = builder.tee(
                f"Flow header {circuit.name}",
                (x - 0.2, y, z),
                plant_storey,
                supply,
                diverging=True,
            )
            builder.pipe(
                flow_source,
                header.ports["in"],
                flow_source_pos,
                header.position,
                plant_storey,
                supply,
            )
            circuit_flow, flow_source = header.ports["branch"], header.ports["out"]
            return_header = builder.tee(
                f"Return header {circuit.name}",
                (x - 0.1, y, z),
                plant_storey,
                ret,
                diverging=False,
            )
            builder.pipe(
                return_header.ports["out"],
                return_target,
                return_header.position,
                return_target_pos,
                plant_storey,
                ret,
            )
            circuit_return, return_target = (
                return_header.ports["branch"],
                return_header.ports["in"],
            )
            flow_source_pos = return_target_pos = header.position
        else:
            circuit_flow, circuit_return = flow_source, return_target

        pump = builder.element(
            "IfcPump",
            name=f"Circulator {circuit.name}",
            type_=pump_type,
            position=(x, y, z),
            storey=plant_storey,
            space="Kitchen5",
            ports={"in": "SINK", "out": "SOURCE"},
            systems=[supply],
        )
        mixing = builder.element(
            "IfcValve",
            name=f"Mixing valve {circuit.name}",
            type_=mixing_type,
            position=(x, y, z + 0.3),
            storey=plant_storey,
            space="Kitchen5",
            ports={"in": "SINK", "bypass": "SINK", "out": "SOURCE"},
            systems=[supply, ret],
        )
        sensor = builder.element(
            "IfcSensor",
            name=f"Flow temperature sensor {circuit.name}",
            type_=sensor_type,
            position=(x, y, z + 0.6),
            storey=plant_storey,
            space="Kitchen5",
            ports={"in": "SINK", "out": "SOURCE"},
            systems=[supply],
            size=(0.05, 0.05, 0.1),
        )
        builder.pipe(
            circuit_flow,
            pump.ports["in"],
            (x - 0.2, y, z),
            (x, y, z),
            plant_storey,
            supply,
        )
        builder.pipe(
            pump.ports["out"],
            mixing.ports["in"],
            (x, y, z),
            (x, y, z + 0.3),
            plant_storey,
            supply,
        )
        builder.pipe(
            mixing.ports["out"],
            sensor.ports["in"],
            (x, y, z + 0.3),
            (x, y, z + 0.6),
            plant_storey,
            supply,
        )
        bypass = builder.tee(
            f"Bypass tee {circuit.name}",
            (x + 0.1, y, z + 0.3),
            plant_storey,
            ret,
            diverging=True,
        )
        builder.pipe(
            bypass.ports["branch"],
            mixing.ports["bypass"],
            (x + 0.1, y, z + 0.3),
            (x, y, z + 0.3),
            plant_storey,
            ret,
        )
        builder.pipe(
            bypass.ports["out"],
            circuit_return,
            (x + 0.1, y, z + 0.3),
            (x - 0.1, y, z),
            plant_storey,
            ret,
        )

        # Distribution mains with one tee per radiator branch.
        flow_main, return_main = sensor.ports["out"], bypass.ports["in"]
        flow_pos: Point = (x, y, z + 0.6)
        return_pos: Point = (x + 0.1, y, z + 0.3)
        for number, spec in enumerate(circuit.radiators, start=1):
            rx, ry, rz = spec.position
            branch_flow = builder.tee(
                f"Flow tee {circuit.name}.{number}",
                (rx, ry - 0.1, rz + 0.65),
                circuit.storey,
                supply,
                diverging=True,
            )
            branch_return = builder.tee(
                f"Return tee {circuit.name}.{number}",
                (rx, ry - 0.1, rz - 0.05),
                circuit.storey,
                ret,
                diverging=False,
            )
            builder.pipe(
                flow_main,
                branch_flow.ports["in"],
                flow_pos,
                branch_flow.position,
                circuit.storey,
                supply,
            )
            builder.pipe(
                branch_return.ports["out"],
                return_main,
                branch_return.position,
                return_pos,
                circuit.storey,
                ret,
            )
            trv = builder.element(
                "IfcValve",
                name=f"Radiator valve {circuit.name}.{number}",
                type_=trv_type,
                position=(rx - spec.type.size[0] / 2, ry, rz + 0.55),
                storey=circuit.storey,
                space=spec.space,
                ports={"in": "SINK", "out": "SOURCE"},
                systems=[supply],
                size=(0.05, 0.05, 0.08),
            )
            radiator = builder.element(
                "IfcSpaceHeater",
                name=f"Radiator {spec.space} {number}",
                type_=builder.element_type(
                    "IfcSpaceHeater",
                    spec.type.name,
                    "RADIATOR",
                    {
                        "Pset_SpaceHeaterTypeCommon": {
                            "OutputCapacity": spec.type.output_capacity,
                            "HeatTransferMedium": "WATER",
                            "EnergySource": "GAS",
                            "PlacementType": "WALL",
                        },
                        "Pset_SpaceHeaterTypeRadiator": {"RadiatorType": "PANEL"},
                    },
                ),
                position=spec.position,
                storey=circuit.storey,
                space=spec.space,
                ports={"flow": "SINK", "return": "SOURCE"},
                systems=[supply, ret],
                size=spec.type.size,
            )
            for port_name, temperature in (
                ("flow", SUPPLY_TEMPERATURE),
                ("return", RETURN_TEMPERATURE),
            ):
                builder._add_pset(
                    radiator.ports[port_name],
                    "Pset_DistributionPortTypePipe",
                    {"NominalDiameter": 0.015, "Temperature": temperature},
                )
            builder.pipe(
                branch_flow.ports["branch"],
                trv.ports["in"],
                branch_flow.position,
                trv.position,
                circuit.storey,
                supply,
            )
            builder.pipe(
                trv.ports["out"],
                radiator.ports["flow"],
                trv.position,
                spec.position,
                circuit.storey,
                supply,
            )
            builder.pipe(
                radiator.ports["return"],
                branch_return.ports["branch"],
                spec.position,
                branch_return.position,
                circuit.storey,
                ret,
            )
            flow_main, flow_pos = branch_flow.ports["out"], branch_flow.position
            return_main, return_pos = branch_return.ports["in"], branch_return.position
        # Cap the mains: the last tee's run outlet/inlet is closed by a bend
        # back into the last branch, which keeps every port connected.
        _cap(builder, flow_main, return_main, flow_pos, circuit.storey, supply, ret)

    builder.pipe(
        boiler.ports["flow"],
        flow_iso.ports["in"],
        BOILER_POSITION,
        (0.45, 3.8, 0.6),
        plant_storey,
        plant_systems[0],
    )
    builder.pipe(
        return_iso.ports["out"],
        boiler.ports["return"],
        (0.55, 3.8, 0.6),
        BOILER_POSITION,
        plant_storey,
        plant_systems[1],
    )
    for system in plant_systems:
        ifcopenshell.api.system.assign_system(
            builder.file,
            products=[boiler.entity, flow_iso.entity, return_iso.entity],
            system=system,
        )
    return builder.file


def _cap(  # noqa: PLR0913
    builder: HeatingModelBuilder,
    flow_end: ifcopenshell.entity_instance,
    return_end: ifcopenshell.entity_instance,
    position: Point,
    storey: str,
    supply: ifcopenshell.entity_instance,
    ret: ifcopenshell.entity_instance,
) -> None:
    """Close the end of the flow and return mains with end caps."""
    cap_type = builder.element_type("IfcPipeFitting", "End cap DN15", "OBSTRUCTION")
    for port, direction, system in (
        (flow_end, "SINK", supply),
        (return_end, "SOURCE", ret),
    ):
        cap = builder.element(
            "IfcPipeFitting",
            name="End cap",
            type_=cap_type,
            position=position,
            storey=storey,
            ports={"end": direction},
            systems=[system],
            size=(0.03, 0.03, 0.03),
        )
        if direction == "SINK":
            ifcopenshell.api.system.connect_port(
                builder.file, port, cap.ports["end"], "SOURCE"
            )
        else:
            ifcopenshell.api.system.connect_port(
                builder.file, cap.ports["end"], port, "SOURCE"
            )


def write(path: Path, architecture_path: Path = ARCHITECTURE_MODEL) -> Path:
    builder_file = build(architecture_path)
    keep = {
        e.GlobalId
        for e in ifcopenshell.open(str(architecture_path)).by_type("IfcRoot")
        if e.is_a("IfcSpatialElement") or e.is_a("IfcProject")
    }
    for entity in sorted(builder_file.by_type("IfcRoot"), key=lambda e: e.id()):
        if entity.GlobalId not in keep:
            entity.GlobalId = ifcopenshell.guid.compress(
                uuid.uuid5(GUID_NAMESPACE, str(entity.id())).hex
            )
    _sort_unordered_sets(builder_file)
    builder_file.write(str(path))
    return path


def _sort_unordered_sets(ifc_file: ifcopenshell.file) -> None:
    """Sort the aggregates ifcopenshell.api fills in hash order.

    Relationship members and unit assignments are unordered SETs in IFC, so
    sorting them by instance id keeps their meaning. Nested ports (IfcRelNests,
    an ordered LIST) are sorted back into creation order. This makes the
    output byte-for-byte reproducible.
    """
    entities = [
        *ifc_file.by_type("IfcRelationship"),
        *ifc_file.by_type("IfcUnitAssignment"),
    ]
    for entity in entities:
        for index, value in enumerate(entity):
            if (
                isinstance(value, tuple)
                and value
                and all(isinstance(v, ifcopenshell.entity_instance) for v in value)
            ):
                entity[index] = tuple(sorted(value, key=lambda v: v.id()))


if __name__ == "__main__":
    write(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ExampleHOM_heating.ifc"))
