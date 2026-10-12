# Realistic model

This tutorial uses a realistic BIM model: the duplex apartment sample model, a two-storey dwelling with many rooms
(`Duplex_A.ifc` in `tests/models/space_boundary`).

![Duplex apartment](./img/duplex_1.png)

![Duplex apartment](./img/duplex_2.png)

```python
from pathlib import Path

from ifctrano.building import Building

building = Building.from_ifc(Path("Duplex_A.ifc"))
building.save_model()
```

or

```bash
ifctrano create Duplex_A.ifc --show-space-boundaries --simulate-model
```

The space boundaries derived from the geometry:

![Space boundaries](./img/duplex_3.png)

The generated model in OpenModelica (taken with an earlier version; the layout may differ):

![Generated model](./img/duplex_6.png)

## Results

Free-floating zones (the model has no heating) for the first ten days of January.

{!tutorials/figures/realistic.html!}

{!tutorials/figures/realistic.md!}
