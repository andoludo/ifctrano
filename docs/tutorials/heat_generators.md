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

**What to expect.** Both generators feed the same radiators, controlled to the same set points, so the rooms should be
as warm in both cases. The difference is the energy bought: natural gas for the boiler, electricity for the heat
pump, which takes most of its heat from the outdoor air.

**What the simulation shows.** Over days 3 to 10, the rooms are equally warm with both generators (18.6 °C on average,
between the 15.85 °C setback and the 21 °C set point) and the radiators deliver the same 125 kWh. The boiler burns
190 kWh of natural gas to produce 148 kWh of heat; the heat pump produces 124 kWh from 36 kWh of electricity, a
coefficient of performance of about 3.4 in these January days. The heat pump also loses less heat in the circuits
(the generator heat is close to the heat of the radiators) and gives a lower peak at the morning reheat (2.8 kW
against 4.4 kW).

