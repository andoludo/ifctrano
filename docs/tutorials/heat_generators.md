# Heat generators

IFC has no heat-pump class: heat pumps are usually exported as `IfcUnitaryEquipment`, which ifctrano recognises from
their type, name or classification (see [How ifctrano works](../explanation/index.md#systems)). When the model does
not say which kind of generator it contains, it can be given explicitly. This example heats ExampleHOM with the
heating model of the [heating tutorial](heating_model.md), first with its gas boiler, then with an air-to-water heat
pump on the same circuits.

```python
from pathlib import Path

from ifctrano.building import Building
from ifctrano.hvac import HeatingOptions, ProductionKind

building = Building.from_ifc(
    Path("ExampleHOM.ifc"),
    hvac_file_paths=[Path("ExampleHOM_heating.ifc")],
    heating_options=HeatingOptions(heat_generator=ProductionKind.air_water_heat_pump),
)
building.save_model()
```

or, from the command line:

```bash
ifctrano create ExampleHOM.ifc --hvac ExampleHOM_heating.ifc --heat-generator air_water_heat_pump
```

Everything else (radiators, valves, circulators, mixing valves and their controls) is the same in both models.

{!tutorials/figures/heat_generators.html!}

{!tutorials/figures/heat_generators.md!}
