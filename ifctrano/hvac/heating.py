"""Hydronic heating systems extracted from IFC distribution networks.

The IFC network (boiler, pumps, valves, hundreds of pipes and fittings, and
radiators) is reduced to the components trano models. Emitters are grouped
into *circuits*: emitters fed by the same heat generator through the same
circulator and mixing valve. Each circuit becomes trano's hydronic circuit
template::

    boiler -> pump -> three-way valve -> temperature sensor -> radiators
    radiator valves -> split valve (collector) -> boiler and three-way valve

Radiators of a space are lumped into one equivalent emitter, as is usual in
building energy simulation. Emitters that are not hydronically connected to a
heat generator become ideal emitters. Values the model does not provide are
left to trano's defaults; every such assumption is recorded in
``HeatingSystem.assumptions`` and logged.
"""

import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
from ifcopenshell import entity_instance
from pydantic import Field

from ifctrano.base import BaseModelConfig
from ifctrano.hvac.network import (
    DistributionNetwork,
    ProductionKind,
    Role,
    production_kind,
)
from ifctrano.hvac.spaces import SpaceLocator, ifc_file_of
from ifctrano.space_boundary import Space

logger = logging.getLogger(__name__)

WATER_DENSITY = 1000.0  # kg/m3
IDEAL_EMITTER_VARIANT = "idealbus"


def _unit_scale(ifc_file: ifcopenshell.file, unit_type: str) -> float:
    try:
        return float(ifcopenshell.util.unit.calculate_unit_scale(ifc_file, unit_type))
    except Exception:
        return 1.0


def _property(
    element: entity_instance, psets: Sequence[str], name: str
) -> Any:  # noqa: ANN401
    """Value of a property from the element or its type; upper bound for ranges."""
    all_psets = ifcopenshell.util.element.get_psets(element)
    for pset in psets:
        value = all_psets.get(pset, {}).get(name)
        if isinstance(value, dict):  # IfcPropertyBoundedValue
            bound = value.get("UpperBoundValue") or value.get("SetPointValue")
            value = getattr(bound, "wrappedValue", bound)
        if value is not None:
            return value
    return None


def _scaled(
    element: entity_instance, psets: Sequence[str], name: str, unit_type: str
) -> float | None:
    value = _property(element, psets, name)
    if value is None:
        return None
    return float(value) * _unit_scale(ifc_file_of(element), unit_type)


class Emitter(BaseModelConfig):
    element: entity_instance
    space: Space | None
    output_capacity: float | None

    @classmethod
    def from_element(cls, element: entity_instance, locator: SpaceLocator) -> "Emitter":
        return cls(
            element=element,
            space=locator.locate(element),
            output_capacity=_scaled(
                element, ["Pset_SpaceHeaterTypeCommon"], "OutputCapacity", "POWERUNIT"
            ),
        )


class Circuit(BaseModelConfig):
    production: entity_instance
    pump: entity_instance | None
    mixing_valve: entity_instance | None
    emitters: list[Emitter] = Field(default_factory=list)


class HeatingSystem(BaseModelConfig):
    circuits: list[Circuit] = Field(default_factory=list)
    ideal_emitters: list[Emitter] = Field(default_factory=list)
    unassigned_emitters: list[Emitter] = Field(default_factory=list)
    network: DistributionNetwork
    assumptions: list[str] = Field(default_factory=list)

    @classmethod
    def from_ifc(
        cls, ifc_files: Iterable[ifcopenshell.file], spaces: Sequence[Space]
    ) -> "HeatingSystem | None":
        network = DistributionNetwork.from_ifc(ifc_files)
        emitters_ = network.elements(Role.emitter)
        if not emitters_:
            return None
        locator = SpaceLocator(spaces)
        productions = network.elements(Role.production)
        circuits: dict[tuple[str, ...], Circuit] = {}
        ideal, unassigned = [], []
        for element in emitters_:
            emitter = Emitter.from_element(element, locator)
            if emitter.space is None:
                unassigned.append(emitter)
                continue
            paths = [
                path
                for production in productions
                if (path := network.supply_path(production, element)) is not None
            ]
            if not paths:
                ideal.append(emitter)
                continue
            path = min(paths, key=len)
            # Circulators may sit in the flow or in the return pipe: take the
            # one closest to the emitter on the flow path, else on the return.
            return_path = network.supply_path(element, path[0]) or []
            pump = network.first(reversed(path), Role.pump) or network.first(
                return_path, Role.pump
            )
            mixing_valve = network.first(
                reversed(path), Role.mixing_valve
            ) or network.first(return_path, Role.mixing_valve)
            key = tuple(
                getattr(n, "GlobalId", "") for n in (path[0], pump, mixing_valve)
            )
            circuit = circuits.setdefault(
                key,
                Circuit(production=path[0], pump=pump, mixing_valve=mixing_valve),
            )
            circuit.emitters.append(emitter)
        system = cls(
            circuits=[circuits[key] for key in sorted(circuits)],
            ideal_emitters=ideal,
            unassigned_emitters=unassigned,
            network=network,
        )
        system._log_summary()
        return system

    def _assume(self, message: str) -> None:
        if message not in self.assumptions:
            self.assumptions.append(message)
            logger.warning(message)

    def _log_summary(self) -> None:
        for emitter in self.unassigned_emitters:
            self._assume(
                f"Emitter {emitter.element.GlobalId} ({emitter.element.Name}) is not "
                "located in any space and is ignored."
            )
        for emitter in self.ideal_emitters:
            self._assume(
                f"Emitter {emitter.element.GlobalId} ({emitter.element.Name}) is not "
                "connected to a heat generator; it is modelled as an ideal emitter."
            )

    # -- trano configuration ----------------------------------------------

    def to_config(
        self, space_ids: Iterable[str]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
        """trano ``emissions`` per space id and the ``systems`` list."""
        space_ids = set(space_ids)
        emissions: dict[str, list[dict[str, Any]]] = {}
        systems: list[dict[str, Any]] = []
        assigned = self._assign_spaces(space_ids)
        circuits_by_production: dict[str, list[tuple[int, Circuit]]] = defaultdict(list)
        for index, circuit in enumerate(self.circuits, start=1):
            if any(c is circuit for c in assigned.values()):
                circuits_by_production[circuit.production.GlobalId].append(
                    (index, circuit)
                )

        for number, circuits in enumerate(circuits_by_production.values(), start=1):
            production = circuits[0][1].production
            boiler_id = f"boiler_{number}"
            circuit_systems: list[dict[str, Any]] = []
            collector_ids = []
            circuit_powers: list[float | None] = []
            for index, circuit in circuits:
                spaces = sorted(
                    space_id for space_id, c in assigned.items() if c is circuit
                )
                pump_id, valve_id = f"pump_{index}", f"three_way_valve_{index}"
                sensor_id, collector_id = (
                    f"temperature_sensor_{index}",
                    f"split_valve_{index}",
                )
                collector_ids.append(collector_id)
                for space_id in spaces:
                    power = self._space_power(space_id)
                    circuit_powers.append(power)
                    emissions[space_id] = self._hydronic_emission(space_id, power)
                circuit_systems += [
                    self._pump(circuit, pump_id, boiler_id),
                    {
                        "three_way_valve": {
                            "id": valve_id,
                            "control": {
                                "three_way_valve_control": {
                                    "id": f"three_way_valve_control_{index}"
                                }
                            },
                            "inlets": [collector_id, pump_id],
                            "outlets": [sensor_id],
                        }
                    },
                    {
                        "temperature_sensor": {
                            "id": sensor_id,
                            "outlets": [f"radiator_{s}" for s in spaces],
                        }
                    },
                    {
                        "split_valve": {
                            "id": collector_id,
                            "inlets": [f"valve_{s}" for s in spaces],
                            "outlets": [boiler_id],
                        }
                    },
                ]
                if circuit.mixing_valve is None:
                    self._assume(
                        f"Circuit {index} has no mixing valve in the model; trano's "
                        "circuit template adds one."
                    )
            systems.append(
                self._boiler(production, boiler_id, collector_ids, circuit_powers)
            )
            systems += circuit_systems

        for emitter in self.ideal_emitters:
            if emitter.space is None:
                continue
            ideal_space = emitter.space.space_unique_name()
            if ideal_space in space_ids and ideal_space not in emissions:
                emissions[ideal_space] = self._ideal_emission(ideal_space)
        return emissions, systems

    def _assign_spaces(self, space_ids: set[str]) -> dict[str, Circuit]:
        """Circuit serving each space; the one with most emitters there wins."""
        counts: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        for index, circuit in enumerate(self.circuits):
            for emitter in circuit.emitters:
                space_id = emitter.space.space_unique_name()  # type: ignore[union-attr]
                if space_id in space_ids:
                    counts[space_id][index] += 1
                else:
                    self._assume(
                        f"Emitter {emitter.element.GlobalId} is in space {space_id}, "
                        "which is not part of the model; it is ignored."
                    )
        assigned = {}
        for space_id, by_circuit in counts.items():
            if len(by_circuit) > 1:
                self._assume(
                    f"Space {space_id} is served by several circuits; it is assigned "
                    "to the circuit with most emitters in the space."
                )
            assigned[space_id] = self.circuits[
                max(sorted(by_circuit), key=lambda i: by_circuit[i])
            ]
        return dict(sorted(assigned.items()))

    def _space_emitters(self, space_id: str) -> list[Emitter]:
        return [
            emitter
            for circuit in self.circuits
            for emitter in circuit.emitters
            if emitter.space and emitter.space.space_unique_name() == space_id
        ]

    def _space_power(self, space_id: str) -> float | None:
        capacities = [e.output_capacity for e in self._space_emitters(space_id)]
        if all(capacity is not None for capacity in capacities):
            return round(sum(capacities), 2)  # type: ignore[arg-type]
        self._assume(
            f"Space {space_id} has emitters without OutputCapacity; trano's default "
            "nominal radiator power is used."
        )
        return None

    @staticmethod
    def _hydronic_emission(space_id: str, power: float | None) -> list[dict[str, Any]]:
        radiator: dict[str, Any] = {"id": f"radiator_{space_id}"}
        if power is not None:
            radiator["parameters"] = {
                "nominal_heating_power_positive_for_heating": power
            }
        return [
            {"radiator": radiator},
            {
                "valve": {
                    "id": f"valve_{space_id}",
                    "control": {
                        "emission_control": {"id": f"emission_control_{space_id}"}
                    },
                }
            },
        ]

    @staticmethod
    def _ideal_emission(space_id: str) -> list[dict[str, Any]]:
        return [
            {
                "radiator": {
                    "id": f"radiator_{space_id}",
                    "variant": IDEAL_EMITTER_VARIANT,
                    "control": {
                        "emission_control": {"id": f"emission_control_{space_id}"}
                    },
                }
            }
        ]

    def _pump(self, circuit: Circuit, pump_id: str, boiler_id: str) -> dict[str, Any]:
        pump: dict[str, Any] = {
            "id": pump_id,
            "control": {"collector_control": {"id": f"collector_control_{pump_id}"}},
            "inlets": [boiler_id],
        }
        if circuit.pump is None:
            self._assume(
                f"Circuit {pump_id} has no circulator in the model; trano's default "
                "pump is used."
            )
            return {"pump": pump}
        parameters = {}
        flow_rate = _scaled(
            circuit.pump,
            ["Pset_PumpTypeCommon"],
            "FlowRateRange",
            "VOLUMETRICFLOWRATEUNIT",
        )
        if flow_rate:
            parameters["m_flow_nominal"] = round(flow_rate * WATER_DENSITY, 6)
        head = _scaled(
            circuit.pump,
            ["Pset_PumpTypeCommon"],
            "FlowResistanceRange",
            "PRESSUREUNIT",
        )
        if head:
            parameters["dp_nominal"] = round(head, 2)
        if parameters:
            pump["parameters"] = parameters
        else:
            self._assume(
                f"Pump {circuit.pump.GlobalId} has no FlowRateRange or "
                "FlowResistanceRange; trano's default pump sizing is used."
            )
        return {"pump": pump}

    def _boiler(
        self,
        production: entity_instance,
        boiler_id: str,
        collector_ids: list[str],
        circuit_powers: list[float | None],
    ) -> dict[str, Any]:
        kind = production_kind(production)
        if kind in (ProductionKind.boiler, ProductionKind.generic):
            has_storage = bool(
                _property(production, ["Pset_BoilerTypeCommon"], "IsWaterStorageHeater")
            ) or bool(self.network.neighbours(production, Role.storage))
            variant = "default" if has_storage else "without_storage"
            if kind == ProductionKind.generic:
                self._assume(
                    f"Heat generator {production.GlobalId} ({production.Name}) is a "
                    f"{production.is_a()} with no recognised type; it is modelled "
                    "as a boiler."
                )
        else:
            variant = kind.value
        boiler: dict[str, Any] = {
            "id": boiler_id,
            "variant": variant,
            "control": {"boiler_control": {"id": f"boiler_control_{boiler_id}"}},
            "inlets": collector_ids,
        }
        power = _scaled(
            production,
            ["Pset_BoilerTypeWater", "Pset_BoilerTypeSteam"],
            "HeatOutput",
            "POWERUNIT",
        )
        if power is None and circuit_powers and None not in circuit_powers:
            power = sum(circuit_powers)  # type: ignore[arg-type]
            self._assume(
                f"Heat generator {production.GlobalId} has no HeatOutput; its nominal "
                "power is the sum of the emitters it serves."
            )
        if power is not None:
            boiler["parameters"] = {"nominal_heating_power": round(power, 2)}
        else:
            self._assume(
                f"Heat generator {production.GlobalId} has no HeatOutput; trano's "
                "default nominal power is used."
            )
        return {"boiler": boiler}
