
# 🚀 Installation

## 📦 Install `ifctrano`

!!! warning
    Trano requires python 3.9 or higher and docker to be installed on the system.
            

ifctrano is a Python package that can be installed via pip.

```bash
pip install ifctrano
```

## ✅ Verify Installation

Run the following commands to ensure everything is working:

```bash
ifctrano --help
ifctrano verify
```

---

# 🔧 Optional Dependencies

## 🐳 Docker (for simulation)

To enable model simulation using the official OpenModelica Docker image, install Docker Desktop:

👉 [https://docs.docker.com/desktop/](https://docs.docker.com/desktop/)

Required for using the `--simulate-model` flag.

---

## 🧠 Graphviz (for layout visualization)

`ifctrano` leverages Graphviz to optimize component layout in generated Modelica models. It is optional, but **recommended**.

### 📥 Install on Windows

- Download and install from: [https://graphviz.org/download/](https://graphviz.org/download/)
- Add the Graphviz `bin` folder to your **system `PATH`**.

### 🐧 Install on Linux

```bash
sudo apt update
sudo apt install graphviz
```

---

# ⚙️ Usage

## 📁 Generate Modelica models from IFC

### 🏢 Using the **Buildings** library

```bash
ifctrano create /path/to/your.ifc
```

### 🏫 Using the **IDEAS** library

```bash
ifctrano create /path/to/your.ifc IDEAS
```

### 🧮 Using the **Reduced Order** library

```bash
ifctrano create /path/to/your.ifc reduced_order
```

---

## 🧱 Show Space Boundaries

To visualize the computed space boundaries:

```bash
ifctrano create /path/to/your.ifc --show-space-boundaries
```

---

## 🔁 Simulate the Model

Run a full simulation after model generation:

```bash
ifctrano create /path/to/your.ifc --simulate-model
```

Make sure Docker is installed and running before simulating.
