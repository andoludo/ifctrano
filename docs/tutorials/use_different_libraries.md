# Use different libraries

ifctrano generates models for four Modelica libraries:

| `LIBRARY` | Library | Zone model |
|---|---|---|
| `Buildings` (default) | [Buildings](https://simulationresearch.lbl.gov/modelica/) | Detailed: every surface, layer and window |
| `IDEAS` | [IDEAS](https://github.com/open-ideas/IDEAS) | Detailed: every surface, layer and window |
| `reduced_order` | [AixLib](https://github.com/RWTH-EBC/AixLib) | Reduced order: resistance–capacitance network |
| `iso_13790` | [AixLib](https://github.com/RWTH-EBC/AixLib) | ISO 13790 5R1C simple hourly method |

The library is given to `save_model`:

```python
from pathlib import Path

from ifctrano.building import Building

building = Building.from_ifc(Path("TwoZones.ifc"))
building.save_model(library="IDEAS")
```

or as the second argument of `ifctrano create`:

```bash
ifctrano create TwoZones.ifc IDEAS
```

The IDEAS model of the two zones, as opened in OpenModelica (taken with an earlier version; the layout may differ):

![Generated model](./img/two_zones_6.png)

## Results

The same configuration of the [two zones model](two_zones_model.md) simulated with the four libraries, for the first
ten days of January, without heating. The figure shows the mean air temperature of the two zones.

{!tutorials/figures/libraries.html!}

{!tutorials/figures/libraries.md!}
