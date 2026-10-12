# Orientation of the facades

The orientation of every wall and window comes from the geometry: ifctrano measures the outward normal of each
surface from the north axis of the model (`+y` by default) and converts it to the azimuth of the Modelica libraries
(see [How ifctrano works](../explanation/index.md#orientation)). This example shows its effect on the simulated
temperatures: the same house, without heating, as built and turned by 180°.

The kitchen of ExampleHOM has windows on its south and west facades. Turning the north axis by 180° makes them face
north and east.

```python
from pathlib import Path

from ifctrano.base import Vector
from ifctrano.building import Building

building = Building.from_ifc(Path("ExampleHOM.ifc"))
as_built = building.to_config()
turned = building.to_config(north_axis=Vector(x=0, y=-1, z=0))
```

`north_axis` is the direction of north in the coordinates of the model: `Vector(x=0, y=-1, z=0)` puts north along
`-y`. Both configurations are simulated from 21 March, when the sun is low enough for the facades to make a
difference, in the Uccle weather.

{!tutorials/figures/orientation.html!}

{!tutorials/figures/orientation.md!}

**What to expect.** In late March the sun is low in the south during the day and sets in the west: a room with south
and west windows gets much more solar gain than the same room facing north and east, which only sees the morning sun
on its east window.

**What the simulation shows.** As built, the kitchen averages 24.8 °C over days 83 to 90, peaking at about 39 °C in
the afternoons. Turned by 180°, it averages 22.7 °C (2.1 K less) and peaks at about 32 °C. The night minima differ less
(15.2 °C and 13.8 °C): the difference is the solar gain of the day. The peaks are high because the house has no
heating, no shading and no thermal mass (the default materials, see
[the limitations](../explanation/index.md#assumptions-and-known-limitations)).

**Difference with earlier versions.** Before ifctrano 0.15 the azimuths were turned by 180°: the "as built" case
of this page was then simulated as the "turned" one.

