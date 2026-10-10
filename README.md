# ifctrano - IFC to Energy Simulation Tool

---
📖 **Full Documentation:** 👉 [ifctrano Docs](https://andoludo.github.io/ifctrano/) 
---

Generate Modelica building models directly from IFC files — with support for simulation, visualization, and multiple libraries.

## Overview
ifctrano is yet another **IFC to energy simulation** tool designed to translate **Industry Foundation Classes (IFC)** models into energy simulation models in **Modelica**.

### Key Differentiator
Unlike most translation approaches that rely on **space boundaries (IfcRelSpaceBoundary)** (e.g. see [An automated IFC-based workflow for building energy performance simulation with Modelica](https://www.sciencedirect.com/science/article/abs/pii/S0926580517308282)), ifctrano operates **solely on geometrical representation**. This is crucial because **space boundaries are rarely available** in IFC models. Instead, ifctrano requires at least the definition of **IfcSpace** objects to build energy simulation models.

### Space-Zone Mapping
For now, **each space is considered as a single thermal zone**, and the necessary space boundaries are **automatically generated**.

## Why ifctrano?
✅ No reliance on **IfcRelSpaceBoundary**

✅ Works with **geometric representation** only

✅ Supports **Modelica-based energy simulation**

✅ **Tested on multiple open-source IFC files**


## Open Source IFC Test Files
ifctrano has been tested using open-source IFC files from various repositories:

- 🐋 [BIM Whale IFC Samples](https://github.com/andrewisen/bim-whale-ifc-samples)
- 🏗️ [IfcSampleFiles](https://github.com/youshengCode/IfcSampleFiles)
- 🎭 [BIM2Modelica](https://github.com/UdK-VPT/BIM2Modelica/tree/master/IFC/IFC2X3/UdKB_Unit_Test_Cases)
- 🕸️ [Ifc2Graph Test Files](https://github.com/JBjoernskov/Ifc2Graph/tree/main/test_ifc_files)
- 🔓 [Open Source BIM](https://github.com/opensourceBIM)

## 🚀 Installation

### 📦 Install `ifctrano`

!!! warning
    Trano requires python 3.9 or higher and docker to be installed on the system.
            

ifctrano is a Python package that can be installed via pip.

```bash
pip install ifctrano
```

### ✅ Verify Installation

Run the following commands to ensure everything is working:

```bash
ifctrano --help
ifctrano verify
```

---

## 🔧 Optional Dependencies

### 🐳 Docker (for simulation)

To enable model simulation using the official OpenModelica Docker image, install Docker Desktop:

👉 [https://docs.docker.com/desktop/](https://docs.docker.com/desktop/)

Required for using the `--simulate-model` flag.

---

### 🧠 Graphviz (for layout visualization)

`ifctrano` leverages Graphviz to optimize component layout in generated Modelica models. It is optional, but **recommended**.

#### 📥 Install on Windows

- Download and install from: [https://graphviz.org/download/](https://graphviz.org/download/)
- Add the Graphviz `bin` folder to your **system `PATH`**.

#### 🐧 Install on Linux

```bash
sudo apt update
sudo apt install graphviz
```

---

## ⚙️ Usage

### 📁 Generate Modelica models from IFC

#### 🏢 Using the **Buildings** library

```bash
ifctrano create /path/to/your.ifc
```

#### 🏫 Using the **IDEAS** library

```bash
ifctrano create /path/to/your.ifc IDEAS
```

#### 🧮 Using the **Reduced Order** library

```bash
ifctrano create /path/to/your.ifc reduced_order
```
---

### 📁 Generate yaml configuration from IFC

Instead of directly generating a Modelica model from an IFC file, this command creates a configuration .yaml file compatible with the Trano
 Python package (https://github.com/andoludo/trano). This configuration file can be reviewed, adapted, and enriched before generating the final Modelica model, allowing for verification and customization of the translation process.
```bash
ifctrano config /path/to/your.ifc
```

Once the YAML configuration file has been generated and adapted, the following command can be used to generate and/or simulate the model.

```bash
ifctrano from-config /path/to/your.yaml
```
---

### 🔥 Include the heating system

Hydronic heating systems modelled with IFC4 MEP conventions (heat generator, circulators, mixing valves, radiators, connected
through `IfcDistributionPort`s) are translated into trano emissions and systems. Heating elements are read from the
architecture file itself, or from federated discipline models sharing its coordinates:

```bash
ifctrano create /path/to/architecture.ifc --hvac /path/to/heating.ifc
ifctrano config /path/to/architecture.ifc --hvac /path/to/heating.ifc
```

Radiators are assigned to spaces by `IfcRelReferencedInSpatialStructure`/`IfcRelContainedInSpatialStructure`, or from
their location. Radiators of a space are lumped into one emitter (`Pset_SpaceHeaterTypeCommon.OutputCapacity` summed),
and each circuit (heat generator, circulator and mixing valve) becomes trano's hydronic circuit. Radiators not connected
to a heat generator become ideal emitters. Values missing from the model fall back to trano defaults, and are logged.

---

### 🧱 Show Space Boundaries

To visualize the computed space boundaries:

```bash
ifctrano create /path/to/your.ifc --show-space-boundaries
```

---

### 🔁 Simulate the Model

Run a full simulation after model generation:

```bash
ifctrano create /path/to/your.ifc --simulate-model
```

Make sure Docker is installed and running before simulating.

---
💡 **ifctrano** aims to make energy simulation model generation from IFC files **simpler, more accessible, and less reliant on incomplete IFC attributes**. 🚀

