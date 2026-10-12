# Control strategies

trano controls every heated room with a PI loop on the air temperature, whose set point a schedule switches between an
occupied value and a setback value (see [How ifctrano works](../explanation/index.md#control)). By default the rooms
are heated to 21 °C from 7:00 to 19:00 and to 15.85 °C at night. The configuration written by ifctrano can be edited
to change this; this example compares the default night setback with a constant set point, on ExampleHOM with its
heating model.

Write the configuration:

```bash
ifctrano config ExampleHOM.ifc --hvac ExampleHOM_heating.ifc
```

and set the setback temperature to the set point in the emission control of each space:

```yaml
spaces:
- id: space_living1_v3g
  emissions:
  - radiator:
      id: radiator_space_living1_v3g
      parameters:
        nominal_heating_power_positive_for_heating: 3360.0
  - valve:
      id: valve_space_living1_v3g
      control:
        emission_control:
          id: emission_control_space_living1_v3g
          parameters:
            temperature_heating_setback: 294.15
```

then build (and simulate) the model from the edited configuration:

```bash
ifctrano from-config ExampleHOM.yaml --simulate-model
```

The other parameters of the emission control are `temperature_heating_setpoint` (294.15 K), `schedule`
(`3600*{7, 19}`, the switching times in seconds of the day) and `controller_gain` (5).

{!tutorials/figures/control.html!}

{!tutorials/figures/control.md!}

**What to expect.** With the night setback, the rooms cool down at night and are heated up again at 7:00, which takes
a power peak; with a constant set point the rooms stay at 21 °C and the radiators deliver a steadier, higher heat.

**What the simulation shows.** Over days 3 to 10, the living room averages 18.6 °C with the night setback (15.0 °C at
night) and 20.9 °C with the constant set point (never below 19.9 °C). Keeping the house at 21 °C needs 162 kWh of
radiator heat instead of 125 kWh (30 % more) and 229 kWh of gas instead of 190 kWh (21 % more). The peak heat is lower
with the constant set point, 1.6 kW instead of 4.4 kW: the night setback saves energy but asks for a morning reheat.

