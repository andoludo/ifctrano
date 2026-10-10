from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import ifcopenshell
import ifcopenshell.api.classification
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.system
import ifcopenshell.util.element
import ifcopenshell.util.system
import ifcopenshell.validate
import pytest
import yaml
from deepdiff import DeepDiff
from _pytest.fixtures import FixtureRequest
from trano.data_models.conversion import convert_network  # type: ignore
from trano.elements.library.library import Library  # type: ignore

from ifctrano.base import Vector
from ifctrano.building import Building
from ifctrano.exceptions import IfcFileNotFoundError, NoIfcSpaceFoundError
from ifctrano.hvac import HeatingOptions, ProductionKind
from ifctrano.hvac.network import DistributionNetwork, Role, production_kind
from ifctrano.hvac.spaces import SpaceLocator
from tests.conftest import CONFIG_PATH, OVERWRITE_RESULTS, SPACE_BOUNDARY_IFC
from tests.hvac import example_hom_heating
from tests.hvac.external import DIGITALHUB_HEATING, DIGITALHUB_URL, fetch

MEP_IFC = Path(__file__).parent / "models" / "mep"
EXAMPLE_HOM = SPACE_BOUNDARY_IFC / "ExampleHOM.ifc"
GROUND_FLOOR = {"Living1", "Kitchen5", "WC4", "Corridor3", "Hobby2"}
FIRST_FLOOR = {"Bedroom6", "Children10", "Bath9", "Corridor8", "Children7"}


@pytest.fixture(scope="module")
def example_hom_heating_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return example_hom_heating.write(
        tmp_path_factory.mktemp("hvac") / "ExampleHOM_heating.ifc"
    )


@pytest.fixture(scope="module")
def example_hom_with_heating(example_hom_heating_path: Path) -> Building:
    return Building.from_ifc(EXAMPLE_HOM, hvac_file_paths=[example_hom_heating_path])


def _spaces(building: Building) -> list[dict]:  # type: ignore[type-arg]
    return building.to_config()["spaces"]  # type: ignore[no-any-return]


def _heating_config(building: Building) -> dict:  # type: ignore[type-arg]
    """The heating part of the configuration: emissions per space and systems."""
    config = building.to_config()
    return {
        "emissions": {
            space["id"]: space["emissions"]
            for space in config["spaces"]
            if "emissions" in space
        },
        "systems": config.get("systems", []),
    }


def compare_heating_config(building: Building, request: FixtureRequest) -> bool:
    file_path = CONFIG_PATH / f"{request.node.name}.yaml"
    if OVERWRITE_RESULTS:
        file_path.write_text(yaml.safe_dump(_heating_config(building)))
    expected = yaml.safe_load(file_path.read_text())
    return not DeepDiff(expected, _heating_config(building), ignore_order=True)


def test_generated_heating_model_is_valid_ifc4(example_hom_heating_path: Path) -> None:
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(
        ifcopenshell.open(str(example_hom_heating_path)), logger, express_rules=True
    )
    # The only issues are the space GlobalIds, copied as-is from ExampleHOM.ifc
    # (where they are already not valid base64) to keep the models federated.
    issues = [
        statement
        for statement in logger.statements
        if not (
            "IfcSpace(" in statement["message"]
            and "GlobalId should be valid base64" in statement["message"]
        )
    ]
    assert issues == []


def test_generated_heating_model_is_deterministic(
    example_hom_heating_path: Path, tmp_path: Path
) -> None:
    again = example_hom_heating.write(tmp_path / "again.ifc")
    assert again.read_bytes() == example_hom_heating_path.read_bytes()


def test_generated_heating_model_shares_spatial_structure(
    example_hom_heating_path: Path,
) -> None:
    architecture = ifcopenshell.open(str(EXAMPLE_HOM))
    heating = ifcopenshell.open(str(example_hom_heating_path))
    for ifc_class in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"):
        assert {e.GlobalId for e in heating.by_type(ifc_class)} == {
            e.GlobalId for e in architecture.by_type(ifc_class)
        }


def test_network_roles(example_hom_heating_path: Path) -> None:
    network = DistributionNetwork.from_ifc(
        [ifcopenshell.open(str(example_hom_heating_path))]
    )
    roles = Counter(network.roles.values())
    assert roles[Role.production] == 1
    assert roles[Role.pump] == 2
    assert roles[Role.mixing_valve] == 2
    assert roles[Role.emitter] == 11
    assert all(network.is_connected(node) for node in network.graph.nodes)


def test_heating_circuits(example_hom_with_heating: Building) -> None:
    heating = example_hom_with_heating.heating
    assert heating is not None
    assert heating.ideal_emitters == []
    assert heating.unassigned_emitters == []
    circuits = {
        frozenset(e.space.name for e in c.emitters): c  # type: ignore[union-attr]
        for c in heating.circuits
    }
    assert set(circuits) == {frozenset(GROUND_FLOOR), frozenset(FIRST_FLOOR)}
    for circuit in circuits.values():
        assert circuit.production.is_a("IfcBoiler")
        assert circuit.pump is not None
        assert circuit.mixing_valve is not None
    assert heating.assumptions == []


def test_geometric_space_location_matches_relations(
    example_hom_with_heating: Building,
) -> None:
    heating = example_hom_with_heating.heating
    assert heating is not None
    locator = SpaceLocator(
        [sb.space for sb in example_hom_with_heating.space_boundaries]
    )
    for circuit in heating.circuits:
        for emitter in circuit.emitters:
            located = locator._locate_geometrically(emitter.element)
            assert located is not None
            assert located.global_id == emitter.space.global_id  # type: ignore[union-attr]


def test_heating_configuration(
    example_hom_with_heating: Building, request: FixtureRequest
) -> None:
    spaces = {space["id"]: space for space in _spaces(example_hom_with_heating)}
    living = next(s for s in spaces if s.startswith("space_living1"))
    radiator = spaces[living]["emissions"][0]["radiator"]
    assert radiator["parameters"]["nominal_heating_power_positive_for_heating"] == (
        2 * example_hom_heating.PANEL_22_1000.output_capacity
    )
    attic = next(s for s in spaces.values() if s["id"].startswith("space_att"))
    assert "emissions" not in attic
    assert compare_heating_config(example_hom_with_heating, request)


def test_heating_configuration_round_trip(example_hom_with_heating: Building) -> None:
    with TemporaryDirectory() as directory:
        config_path = Path(directory) / f"{example_hom_with_heating.name}.yaml"
        example_hom_with_heating.to_yaml(config_path)
        model = convert_network(
            config_path.stem,
            config_path,
            library=Library.from_configuration("Buildings"),
        ).model()
    for component in ("boiler_1", "pump_1", "three_way_valve_2", "split_valve_2"):
        assert component in model.lower()


def test_heating_network(example_hom_with_heating: Building) -> None:
    model = example_hom_with_heating.create_network(library="Buildings").model()
    assert "radiator_space_living1" in model.lower()


def test_single_file_heating_model() -> None:
    building = Building.from_ifc(MEP_IFC / "b03_heating_with_building_blenderBIM.ifc")
    heating = building.heating
    assert heating is not None
    assert len(heating.circuits) == 2
    assert sum(len(c.emitters) for c in heating.circuits) == 7
    config = building.to_config()
    boiler = config["systems"][0]["boiler"]
    # The boiler is a storage heater (Pset_BoilerTypeCommon.IsWaterStorageHeater)
    # without HeatOutput: its power is the sum of the radiators it serves.
    assert boiler["variant"] == "default"
    assert boiler["parameters"]["nominal_heating_power"] == 7 * 10000.0
    assert building.create_network(library="Buildings").model()


def test_unconnected_radiator_is_ideal() -> None:
    building = Building.from_ifc(MEP_IFC / "ExampleHOM_with_radiator.ifc")
    heating = building.heating
    assert heating is not None
    assert heating.circuits == []
    assert len(heating.ideal_emitters) == 1
    config = building.to_config()
    assert "systems" not in config
    emissions = [s["emissions"] for s in config["spaces"] if "emissions" in s]
    assert emissions == [
        [
            {
                "radiator": {
                    "id": "radiator_space_corridor3_n2a",
                    "variant": "idealbus",
                    "control": {
                        "emission_control": {
                            "id": "emission_control_space_corridor3_n2a"
                        }
                    },
                }
            }
        ]
    ]
    assert building.create_network(library="Buildings").model()


def test_heating_only_model_has_no_spaces() -> None:
    with pytest.raises(NoIfcSpaceFoundError):
        Building.from_ifc(
            MEP_IFC / "KM_DPM_Vereinshaus_Gruppe62_Heizung_with_pumps.ifc"
        )


def test_missing_hvac_file() -> None:
    with pytest.raises(IfcFileNotFoundError):
        Building.from_ifc(EXAMPLE_HOM, hvac_file_paths=[Path("missing_heating.ifc")])


def test_model_without_heating() -> None:
    building = Building.from_ifc(EXAMPLE_HOM)
    assert building.heating is None
    assert "systems" not in building.to_config()


@pytest.mark.large
def test_digitalhub_federated_heating() -> None:
    heating_path = fetch(DIGITALHUB_URL, *DIGITALHUB_HEATING)
    building = Building.from_ifc(
        SPACE_BOUNDARY_IFC / "FM_ARC_DigitalHub_with_SB_neu.ifc",
        hvac_file_paths=[heating_path],
        # The Vitocal 350-G is a ground source heat pump, exported as an
        # IfcUnitaryEquipment whose name does not say so (IFC has no heat-pump
        # class): its kind is given explicitly.
        heating_options=HeatingOptions(
            heat_generator=ProductionKind.water_water_heat_pump
        ),
    )
    heating = building.heating
    assert heating is not None
    emitters = [e for c in heating.circuits for e in c.emitters]
    # Real-world Revit export: 63 radiators, one of them not connected to the
    # heat pump, four circuits behind 3-way valves. Part of the pipes are drawn
    # against the flow; every circuit is still found with the circulator
    # driving it.
    assert len(heating.unassigned_emitters) == 0
    assert len(heating.ideal_emitters) == 1
    assert len(emitters) == 62
    assert len(heating.circuits) == 4
    assert all(c.mixing_valve is not None for c in heating.circuits)
    assert all(c.pump is not None for c in heating.circuits)
    assert {c.production.is_a() for c in heating.circuits} == {"IfcUnitaryEquipment"}
    config = building.to_config()
    assert config["systems"][0]["boiler"]["variant"] == "water_water_heat_pump"
    # The model has no radiator outputs nor pump flows: they are sized from the
    # design heat loads of the spaces.
    assert any("design heat load" in a for a in heating.assumptions)
    pumps = [s["pump"] for s in config["systems"] if "pump" in s]
    assert all(pump["parameters"]["m_flow_nominal"] > 0 for pump in pumps)
    assert building.create_network(library="Buildings").model()


@pytest.mark.parametrize(
    ("ifc_class", "attributes", "classification", "kind"),
    [
        ("IfcBoiler", {"Name": "Gas boiler"}, None, ProductionKind.boiler),
        (
            "IfcUnitaryEquipment",
            {
                "Name": "HP-01",
                "PredefinedType": "USERDEFINED",
                "ObjectType": "HEATPUMP",
            },
            None,
            ProductionKind.water_water_heat_pump,
        ),
        (
            "IfcUnitaryEquipment",
            {"Name": "Unit 2"},
            "Air source heat pumps",
            ProductionKind.air_water_heat_pump,
        ),
        (
            "IfcUnitaryEquipment",
            {"Name": "Viessmann Vitocal-350-G-Pro"},
            None,
            ProductionKind.generic,
        ),
    ],
)
def test_heat_generator_kind(
    ifc_class: str,
    attributes: dict,  # type: ignore[type-arg]
    classification: str | None,
    kind: ProductionKind,
) -> None:
    ifc_file = ifcopenshell.api.project.create_file(version="IFC4")
    ifcopenshell.api.root.create_entity(ifc_file, ifc_class="IfcProject")
    element = ifcopenshell.api.root.create_entity(ifc_file, ifc_class=ifc_class)
    for name, value in attributes.items():
        setattr(element, name, value)
    if classification:
        ifcopenshell.api.classification.add_reference(
            ifc_file,
            products=[element],
            identification="HP",
            name=classification,
            classification=ifcopenshell.api.classification.add_classification(
                ifc_file, classification="Uniclass"
            ),
        )
    assert production_kind(element) == kind


def test_heat_generator_override(example_hom_heating_path: Path) -> None:
    building = Building.from_ifc(
        EXAMPLE_HOM,
        hvac_file_paths=[example_hom_heating_path],
        heating_options=HeatingOptions(
            heat_generator=ProductionKind.air_water_heat_pump
        ),
    )
    boiler = building.to_config()["systems"][0]["boiler"]
    assert boiler["variant"] == "air_water_heat_pump"
    assert building.create_network(library="Buildings").model()


def _mini_network(
    reversed_supply: bool,
) -> tuple[ifcopenshell.file, dict[str, ifcopenshell.entity_instance]]:
    """Boiler, three supply pipes, pump, mixing valve and radiator; the return
    goes through a tee whose branch is the bypass of the mixing valve.

    With ``reversed_supply``, the supply pipes are drawn against the flow, as
    some exporters do: the bypass is then the shortest undirected route from
    the boiler to the radiator, although no circulator drives that flow.
    """
    ifc_file = ifcopenshell.api.project.create_file(version="IFC4")
    elements: dict[str, ifcopenshell.entity_instance] = {}

    def add(name: str, ifc_class: str, predefined_type: str) -> None:
        elements[name] = ifcopenshell.api.root.create_entity(
            ifc_file, ifc_class=ifc_class, name=name, predefined_type=predefined_type
        )

    def port(name: str) -> ifcopenshell.entity_instance:
        return ifcopenshell.api.system.add_port(ifc_file, element=elements[name])

    def connect(
        source: ifcopenshell.entity_instance,
        target: ifcopenshell.entity_instance,
        direction: str = "SOURCE",
    ) -> None:
        ifcopenshell.api.system.connect_port(ifc_file, source, target, direction)

    add("boiler", "IfcBoiler", "WATER")
    add("pump", "IfcPump", "CIRCULATOR")
    add("mixing", "IfcValve", "MIXING")
    add("radiator", "IfcSpaceHeater", "RADIATOR")
    add("tee", "IfcPipeFitting", "JUNCTION")
    for name in ("pipe_1", "pipe_2", "pipe_3"):
        add(name, "IfcPipeSegment", "RIGIDSEGMENT")
    # Supply: boiler -> pipes -> pump, possibly drawn against the flow.
    outlet = port("boiler")
    for name in ("pipe_1", "pipe_2", "pipe_3", "pump"):
        connect(outlet, port(name), "SINK" if reversed_supply else "SOURCE")
        outlet = port(name)
    mixing_inlet, mixing_bypass = port("mixing"), port("mixing")
    connect(outlet, mixing_inlet)
    connect(port("mixing"), port("radiator"))
    # Return: radiator -> tee -> boiler, the tee branch is the mixing bypass.
    connect(port("radiator"), port("tee"))
    connect(port("tee"), mixing_bypass)
    connect(port("tee"), port("boiler"))
    return ifc_file, elements


@pytest.mark.parametrize("reversed_supply", [False, True])
def test_supply_path_goes_through_circulator(reversed_supply: bool) -> None:
    ifc_file, elements = _mini_network(reversed_supply)
    network = DistributionNetwork.from_ifc([ifc_file])
    path = network.supply_path(elements["boiler"], elements["radiator"])
    assert path is not None
    assert [e.Name for e in path if network.roles[e] != Role.passive] == [
        "boiler",
        "pump",
        "mixing",
        "radiator",
    ]


def test_wrongly_directed_pipes(example_hom_heating_path: Path, tmp_path: Path) -> None:
    """The ground floor flow pipes drawn against the flow do not change the circuits."""
    heating = ifcopenshell.open(str(example_hom_heating_path))
    supply = next(
        system
        for system in heating.by_type("IfcDistributionSystem")
        if system.Name == "Heating flow GF"
    )
    flip = {"SOURCE": "SINK", "SINK": "SOURCE"}
    for element in ifcopenshell.util.system.get_system_elements(supply):
        if element.is_a() in (
            "IfcPipeSegment",
            "IfcPipeFitting",
            "IfcPump",
            "IfcSensor",
        ):
            for port in ifcopenshell.util.system.get_ports(element):
                port.FlowDirection = flip[port.FlowDirection]
    path = tmp_path / "reversed.ifc"
    heating.write(str(path))
    building = Building.from_ifc(EXAMPLE_HOM, hvac_file_paths=[path])
    assert building.heating is not None
    circuits = {
        frozenset(e.space.name for e in c.emitters): c  # type: ignore[union-attr]
        for c in building.heating.circuits
    }
    assert set(circuits) == {frozenset(GROUND_FLOOR), frozenset(FIRST_FLOOR)}
    assert all(
        c.pump is not None and c.mixing_valve is not None for c in circuits.values()
    )


def test_sizing_without_output_capacity(
    example_hom_heating_path: Path, tmp_path: Path
) -> None:
    heating = ifcopenshell.open(str(example_hom_heating_path))
    for radiator_type in heating.by_type("IfcSpaceHeaterType"):
        pset = ifcopenshell.util.element.get_pset(
            radiator_type, "Pset_SpaceHeaterTypeCommon"
        )
        ifcopenshell.api.pset.edit_pset(
            heating,
            pset=heating.by_id(pset["id"]),
            properties={"OutputCapacity": None},
        )
    path = tmp_path / "without_capacities.ifc"
    heating.write(str(path))
    building = Building.from_ifc(EXAMPLE_HOM, hvac_file_paths=[path])
    loads = building.design_heat_loads(Vector(x=0, y=1, z=0))
    spaces = {space["id"]: space for space in _spaces(building)}
    heated = {k: v for k, v in spaces.items() if "emissions" in v}
    assert len(heated) == len(GROUND_FLOOR | FIRST_FLOOR)
    for space_id, space in heated.items():
        power = space["emissions"][0]["radiator"]["parameters"][
            "nominal_heating_power_positive_for_heating"
        ]
        assert power == round(loads[space_id])
        assert 100 < power < 2000
    assert building.heating is not None
    assert any("design heat load" in a for a in building.heating.assumptions)
