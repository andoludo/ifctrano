# Installation

## Install ifctrano

ifctrano requires Python 3.11 or 3.12.

```bash
pip install ifctrano
```

Check the installation:

```bash
ifctrano --help
ifctrano verify
```

## Optional dependencies

### Docker (simulation)

ifctrano simulates the generated models with OpenModelica in the official OpenModelica Docker image. Install
[Docker](https://docs.docker.com/get-started/get-docker/) and keep it running to use `--simulate-model`. The Modelica
libraries are installed in the container at its first start, which needs network access.

### Graphviz (layout)

trano uses Graphviz to place the components of the generated Modelica models. It is optional, but the diagrams are
easier to read with it.

- Windows: install it from [graphviz.org](https://graphviz.org/download/) and add its `bin` folder to the `PATH`.
- Linux:

```bash
sudo apt update
sudo apt install graphviz
```

## Usage

ifctrano has four commands:

| Command | Does |
|---|---|
| `ifctrano create MODEL [LIBRARY]` | Builds the Modelica model of an IFC file, next to it. |
| `ifctrano config MODEL` | Writes the trano configuration (YAML) of an IFC file, to review or edit. |
| `ifctrano from-config CONFIG [LIBRARY]` | Builds the Modelica model of a configuration. |
| `ifctrano verify` | Checks the installation. |

`LIBRARY` is `Buildings` (default), `IDEAS`, `reduced_order` or `iso_13790`:

```bash
ifctrano create /path/to/your.ifc
ifctrano create /path/to/your.ifc IDEAS
```

Options of `create`:

| Option | Does |
|---|---|
| `--simulate-model` | Simulates the model in OpenModelica (Docker) and opens an HTML report of the results. |
| `--show-space-boundaries` | Shows the space boundaries computed from the geometry. |
| `--hvac PATH` | Adds a federated heating model (IFC4 MEP); can be given several times. |
| `--heat-generator KIND` | Kind of heat generator: `boiler`, `air_water_heat_pump`, `water_water_heat_pump` or `generic`. |

`config` takes the same `--hvac`, `--heat-generator` and `--show-space-boundaries` options, and `from-config` takes
`--simulate-model`.
