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
