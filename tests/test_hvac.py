from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

import ifcopenshell
import ifcopenshell.validate
import pytest
import yaml
from deepdiff import DeepDiff
from _pytest.fixtures import FixtureRequest
from trano.data_models.conversion import convert_network  # type: ignore
from trano.elements.library.library import Library  # type: ignore

from ifctrano.building import Building
from ifctrano.exceptions import IfcFileNotFoundError, NoIfcSpaceFoundError
from ifctrano.hvac.network import DistributionNetwork, Role
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
    )
    heating = building.heating
    assert heating is not None
    emitters = [e for c in heating.circuits for e in c.emitters]
    # Real-world Revit export: 63 radiators, one of them not connected to the
    # heat pump, four circuits behind 3-way valves, one of them without its own
    # circulator (trano's circuit template adds one).
    assert len(heating.unassigned_emitters) == 0
    assert len(heating.ideal_emitters) == 1
    assert len(emitters) == 62
    assert len(heating.circuits) == 4
    assert all(c.mixing_valve is not None for c in heating.circuits)
    assert sum(c.pump is not None for c in heating.circuits) == 3
    # IFC4 has no heat-pump class; the Vitocal heat pump is an
    # IfcUnitaryEquipment whose name does not say "heat pump".
    assert {c.production.is_a() for c in heating.circuits} == {"IfcUnitaryEquipment"}
    assert building.create_network(library="Buildings").model()
    assert any("no circulator" in assumption for assumption in heating.assumptions)
