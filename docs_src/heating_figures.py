"""Figures of the heating tutorial (docs/tutorials/heating_model.md).

Renders the federated IFC models (ExampleHOM architecture and the generated
heating discipline model) and the hydronic network of the trano model
generated from them.

Run from the repository root (the 3D renders need a display; on a headless
machine use xvfb):

    xvfb-run -a poetry run python docs_src/heating_figures.py
"""

import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.system
import numpy as np
import pydot  # type: ignore
import vedo  # type: ignore
from trano.data_models.conversion import convert_network  # type: ignore
from trano.elements.library.library import Library  # type: ignore

ROOT = Path(__file__).parents[1]
sys.path.append(str(ROOT))
from ifctrano.building import Building  # noqa: E402
from tests.hvac import example_hom_heating  # noqa: E402

IMAGES = ROOT / "docs" / "tutorials" / "img"
ARCHITECTURE = ROOT / "tests" / "models" / "space_boundary" / "ExampleHOM.ifc"

SUPPLY, RETURN = "#d62728", "#1f77b4"
ARCHITECTURE_STYLE = {
    "IfcWall": ("#bdbdbd", 0.18),
    "IfcSlab": ("#9e9e9e", 0.22),
    "IfcWindow": ("#9ecae1", 0.35),
    "IfcDoor": ("#c49c6b", 0.3),
}
HEATING_STYLE = {
    "IfcBoiler": "#3a3a3a",
    "IfcPump": "#2ca02c",
    "IfcSensor": "#ffbf00",
    "IfcSpaceHeater": "#ff7f0e",
}
VALVE_STYLE = {"MIXING": "#9467bd", "REGULATING": "#e377c2", "ISOLATING": "#8c564b"}


def _meshes(
    ifc_file: ifcopenshell.file, classes: tuple[str, ...]
) -> list[tuple[ifcopenshell.entity_instance, vedo.Mesh]]:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    meshes = []
    for element in (e for c in classes for e in ifc_file.by_type(c)):
        if not element.Representation:
            continue
        shape = ifcopenshell.geom.create_shape(settings, element)
        vertices = np.asarray(shape.geometry.verts).reshape(-1, 3)
        faces = np.asarray(shape.geometry.faces).reshape(-1, 3)
        meshes.append((element, vedo.Mesh([vertices, faces])))
    return meshes


def _heating_color(element: ifcopenshell.entity_instance) -> str:
    if element.is_a("IfcValve"):
        return VALVE_STYLE.get(
            ifcopenshell.util.element.get_predefined_type(element), "#7f7f7f"
        )
    for ifc_class, color in HEATING_STYLE.items():
        if element.is_a(ifc_class):
            return color
    systems = ifcopenshell.util.system.get_element_systems(element)
    is_return = any("return" in (s.Name or "").lower() for s in systems)
    return RETURN if is_return else SUPPLY


def render_ifc(heating_path: Path) -> None:
    architecture = ifcopenshell.open(str(ARCHITECTURE))
    heating = ifcopenshell.open(str(heating_path))
    building = []
    for element, mesh in _meshes(architecture, tuple(ARCHITECTURE_STYLE)):
        color, alpha = ARCHITECTURE_STYLE[element.is_a()]
        building.append(mesh.c(color).alpha(alpha).lighting("off"))
    floors = [
        mesh.c("#9e9e9e").alpha(0.12).lighting("off")
        for slab, mesh in _meshes(architecture, ("IfcSlab",))
        if ifcopenshell.util.element.get_predefined_type(slab) != "ROOF"
    ]
    network = [
        mesh.c(_heating_color(element)).lighting("glossy")
        for element, mesh in _meshes(
            heating,
            (
                "IfcBoiler",
                "IfcPump",
                "IfcValve",
                "IfcSensor",
                "IfcSpaceHeater",
                "IfcPipeSegment",
                "IfcPipeFitting",
            ),
        )
    ]
    camera = {
        "position": (-11.0, -16.0, 14.0),
        "focal_point": (4.3, 5.6, 2.6),
        "viewup": (0, 0, 1),
    }
    for name, actors in (
        ("heating_ifc_federated.png", [*building, *network]),
        ("heating_ifc_network.png", [*floors, *network]),
    ):
        plotter = vedo.Plotter(offscreen=True, size=(1600, 1200), bg="white")
        plotter.show(*actors, camera=camera, interactive=False)
        plotter.screenshot(str(IMAGES / name))
        plotter.close()


NODE_STYLE = {
    "Boiler": ("Boiler", "box3d", "#3a3a3a", "white"),
    "Pump": ("Pump", "circle", "#2ca02c", "white"),
    "ThreeWayValve": ("3-way valve", "diamond", "#9467bd", "white"),
    "TemperatureSensor": ("T sensor", "invhouse", "#ffbf00", "black"),
    "Radiator": ("Radiator", "box", "#ff7f0e", "black"),
    "Valve": ("Valve", "diamond", "#e377c2", "black"),
    "SplitValve": ("Collector", "triangle", "#1f77b4", "white"),
    "Space": ("", "folder", "#f0f0f0", "black"),
}


def _label(
    node: object, config: dict, space_names: dict[str, str]  # type: ignore[type-arg]
) -> str:
    kind = type(node).__name__
    name = node.name  # type: ignore[attr-defined]
    title = NODE_STYLE[kind][0]
    if kind == "Space":
        return space_names.get(name, name)
    if kind == "Radiator":
        space = next(s for s in config["spaces"] if f"radiator_{s['id']}" == name)
        power = space["emissions"][0]["radiator"]["parameters"][
            "nominal_heating_power_positive_for_heating"
        ]
        return f"{title}\\n{power:.0f} W"
    if kind == "Boiler":
        boiler = config["systems"][0]["boiler"]
        return (
            f"{title}\\n{boiler['parameters']['nominal_heating_power'] / 1000:.0f} kW"
        )
    return f"{title} {name.rsplit('_', 1)[-1]}" if name[-1].isdigit() else title


def render_hydronic_network(
    config_path: Path, config: dict, space_names: dict[str, str]  # type: ignore[type-arg]
) -> None:
    network = convert_network(
        config_path.stem, config_path, library=Library.from_configuration("Buildings")
    )
    graph = pydot.Dot(
        "heating",
        graph_type="digraph",
        rankdir="LR",
        fontname="Helvetica",
        nodesep="0.15",
        ranksep="0.5",
        bgcolor="white",
    )
    heated = {
        a.name
        for a, b in network.graph.edges
        if {type(a).__name__, type(b).__name__} == {"Space", "Radiator"}
    } | {
        b.name
        for a, b in network.graph.edges
        if {type(a).__name__, type(b).__name__} == {"Space", "Radiator"}
    }
    nodes = [
        n
        for n in network.graph.nodes
        if type(n).__name__ in NODE_STYLE
        and (type(n).__name__ != "Space" or n.name in heated)
    ]
    for node in nodes:
        _, shape, fill, font = NODE_STYLE[type(node).__name__]
        graph.add_node(
            pydot.Node(
                node.name,
                label=_label(node, config, space_names),
                shape=shape,
                style="filled",
                fillcolor=fill,
                fontcolor=font,
                fontname="Helvetica",
                fontsize="11",
            )
        )
    for a, b in network.graph.edges:
        kinds = (type(a).__name__, type(b).__name__)
        if not all(k in NODE_STYLE for k in kinds):
            continue
        if "Space" in kinds:
            if "Radiator" not in kinds:
                continue
            graph.add_edge(
                pydot.Edge(
                    b.name,
                    a.name,
                    style="dotted",
                    color="#7f7f7f",
                    arrowhead="none",
                    label="heat",
                    fontsize="9",
                )
            )
            continue
        returning = kinds[0] in ("Radiator", "Valve", "SplitValve")
        bypass = kinds == ("SplitValve", "ThreeWayValve")
        graph.add_edge(
            pydot.Edge(
                a.name,
                b.name,
                color=RETURN if returning else SUPPLY,
                penwidth="1.6",
                style="dashed" if bypass else "solid",
                constraint=(
                    "false" if bypass or kinds == ("SplitValve", "Boiler") else "true"
                ),
            )
        )
    graph.write_png(str(IMAGES / "heating_hydronic_model.png"))


def main() -> None:
    logging.disable(logging.CRITICAL)
    IMAGES.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as directory:
        heating_path = example_hom_heating.write(
            Path(directory) / "ExampleHOM_heating.ifc"
        )
        render_ifc(heating_path)
        building = Building.from_ifc(ARCHITECTURE, hvac_file_paths=[heating_path])
        config_path = Path(directory) / "examplehom.yaml"
        building.to_yaml(config_path)
        space_names = {
            sb.space.space_unique_name(): sb.space.name or ""
            for sb in building.space_boundaries
        }
        render_hydronic_network(config_path, building.to_config(), space_names)


if __name__ == "__main__":
    main()
