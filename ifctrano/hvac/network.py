"""Port-based connectivity graph of IFC distribution elements.

IFC4 MEP models describe connectivity with ports: every distribution element
nests ``IfcDistributionPort`` instances (``IfcRelNests``) that carry a
``FlowDirection`` and are linked pairwise with ``IfcRelConnectsPorts``. This
module turns that into a directed graph whose nodes are distribution elements
and classifies each element by the role it plays in a hydronic heating system.
Pipes, fittings, isolating valves and sensors are kept in the graph but are
"passive": they only carry the connectivity between active components.
"""

import logging
import re
from collections.abc import Iterable, Sequence
from enum import Enum

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.system
import networkx as nx
from ifcopenshell import entity_instance

logger = logging.getLogger(__name__)

MIXING_VALVE_TYPES = {"MIXING", "DIVERTING", "CHANGEOVER"}
UNDEFINED_TYPES = {None, "NOTDEFINED", "USERDEFINED"}
HEAT_SOURCE_CLASSES = ("IfcBoiler", "IfcUnitaryEquipment", "IfcHeatExchanger")
HEAT_PUMP_PATTERN = re.compile(
    r"heat[\s_-]?pump|w(ä|ae)rmepumpe|warmtepomp|pompe [àa] chaleur", re.IGNORECASE
)
AIR_SOURCE_PATTERN = re.compile(
    r"\bair\b|air[\s_-]?(to|/)?[\s_-]?water|\bluft|lucht|\baero", re.IGNORECASE
)
MINIMUM_MIXING_VALVE_PORTS = 3


class Role(str, Enum):
    production = "production"
    pump = "pump"
    mixing_valve = "mixing_valve"
    emitter = "emitter"
    storage = "storage"
    passive = "passive"


class ProductionKind(str, Enum):
    boiler = "boiler"
    air_water_heat_pump = "air_water_heat_pump"
    water_water_heat_pump = "water_water_heat_pump"
    generic = "generic"


def _descriptions(element: entity_instance) -> str:
    element_type = ifcopenshell.util.element.get_type(element)
    texts = [
        element.Name,
        getattr(element, "ObjectType", None),
        getattr(element_type, "Name", None),
        getattr(element_type, "ElementType", None),
    ]
    return " ".join(text for text in texts if text)


def production_kind(element: entity_instance) -> ProductionKind:
    """Kind of heat generator, from the IFC class first and naming second.

    IFC4 has no heat-pump class, so heat pumps are typically exported as
    ``IfcUnitaryEquipment``; they are recognised from their name or type name.
    """
    description = _descriptions(element)
    if HEAT_PUMP_PATTERN.search(description):
        if AIR_SOURCE_PATTERN.search(description):
            return ProductionKind.air_water_heat_pump
        return ProductionKind.water_water_heat_pump
    if element.is_a("IfcBoiler"):
        return ProductionKind.boiler
    return ProductionKind.generic


ROLES_BY_CLASS = (
    ("IfcSpaceHeater", Role.emitter),
    ("IfcPump", Role.pump),
    ("IfcTank", Role.storage),
    *((ifc_class, Role.production) for ifc_class in HEAT_SOURCE_CLASSES),
)


def _is_mixing_valve(valve: entity_instance) -> bool:
    predefined_type = ifcopenshell.util.element.get_predefined_type(valve)
    if predefined_type in MIXING_VALVE_TYPES:
        return True
    ports = ifcopenshell.util.system.get_ports(valve)
    return (
        predefined_type in UNDEFINED_TYPES and len(ports) >= MINIMUM_MIXING_VALVE_PORTS
    )


def classify(element: entity_instance) -> Role:
    for ifc_class, role in ROLES_BY_CLASS:
        if element.is_a(ifc_class):
            return role
    if element.is_a("IfcValve") and _is_mixing_valve(element):
        return Role.mixing_valve
    return Role.passive


class DistributionNetwork:
    """Directed connectivity graph of the distribution elements of IFC files.

    An edge ``a -> b`` means fluid flows from ``a`` to ``b``. Connections whose
    ports have no consistent ``FlowDirection`` are added in both directions.
    """

    def __init__(self, graph: nx.DiGraph) -> None:
        self.graph = graph
        self.undirected = graph.to_undirected(as_view=True)
        self.roles = {node: classify(node) for node in graph.nodes}

    @classmethod
    def from_ifc(cls, ifc_files: Iterable[ifcopenshell.file]) -> "DistributionNetwork":
        graph = nx.DiGraph()
        for ifc_file in ifc_files:
            graph.add_nodes_from(ifc_file.by_type("IfcDistributionFlowElement"))
            for relation in ifc_file.by_type("IfcRelConnectsPorts"):
                relating = ifcopenshell.util.system.get_port_element(
                    relation.RelatingPort
                )
                related = ifcopenshell.util.system.get_port_element(
                    relation.RelatedPort
                )
                if relating is None or related is None or relating == related:
                    continue
                directions = (
                    relation.RelatingPort.FlowDirection,
                    relation.RelatedPort.FlowDirection,
                )
                if directions == ("SOURCE", "SINK"):
                    graph.add_edge(relating, related)
                elif directions == ("SINK", "SOURCE"):
                    graph.add_edge(related, relating)
                else:
                    graph.add_edge(relating, related)
                    graph.add_edge(related, relating)
        return cls(graph)

    def elements(self, role: Role) -> list[entity_instance]:
        return sorted(
            (node for node, role_ in self.roles.items() if role_ == role),
            key=lambda element: element.GlobalId,
        )

    def is_connected(self, element: entity_instance) -> bool:
        return bool(self.graph.degree(element))

    def supply_path(
        self, source: entity_instance, target: entity_instance
    ) -> Sequence[entity_instance] | None:
        """Shortest flow path from ``source`` to ``target``.

        The path may not pass through other emitters or heat generators. The
        flow direction is followed when the model provides it; otherwise the
        connectivity is used without direction.
        """

        def allowed(node: entity_instance) -> bool:
            return node in (source, target) or self.roles[node] not in (
                Role.emitter,
                Role.production,
            )

        for graph in (self.graph, self.undirected):
            view = nx.subgraph_view(graph, filter_node=allowed)  # type: ignore
            try:
                return list(nx.shortest_path(view, source, target))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        return None

    def first(
        self, elements: Iterable[entity_instance], role: Role
    ) -> entity_instance | None:
        return next((e for e in elements if self.roles[e] == role), None)

    def neighbours(self, element: entity_instance, role: Role) -> list[entity_instance]:
        """Active elements of ``role`` reachable through passive elements only."""
        found, seen, stack = [], {element}, [element]
        while stack:
            for neighbour in self.undirected.neighbors(stack.pop()):
                if neighbour in seen:
                    continue
                seen.add(neighbour)
                if self.roles[neighbour] == role:
                    found.append(neighbour)
                elif self.roles[neighbour] == Role.passive:
                    stack.append(neighbour)
        return found
