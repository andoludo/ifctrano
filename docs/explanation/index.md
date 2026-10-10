# Envelope translation

ifctrano derives the envelope of each space from the geometry of the IFC model: the bounding boxes of the space and of
the elements around it give the surfaces they share. This page explains the conventions used to translate these
surfaces into trano and the Modelica libraries.

## Orientation

The orientation of a surface is given by its outward normal, measured from the north axis of the model (`+y` by
default, see `north_axis`). trano and the Modelica libraries use the azimuth of the Buildings library: radians from
south, positive towards west.

| Facade faces | Azimuth (rad) |
|--------------|---------------|
| South        | 0             |
| West         | π/2 (1.57)    |
| North        | π (3.14)      |
| East         | −π/2 (−1.57)  |

Vertical surfaces are snapped to the closest of the eight main and intermediate directions. The orientation of roofs
and slabs does not change their physics: they are given the azimuth 0.

!!! note
    Before ifctrano 0.15 (trano 0.39), the compass bearing of the normal was written as the azimuth, which turned every
    facade by 180°: north facades were simulated facing south. Models generated with earlier versions should be
    regenerated.

## Surfaces

- **Walls** are gross facade areas, windows included, as trano expects. The walls and windows of a space are merged per
  orientation.
- **Windows** larger than the wall of their orientation (overlapping window boxes on glazed facades) are reduced to 90%
  of the wall area. A wall is added where a space has windows without walls.
- **Floors on ground**, **roofs** and **internal walls** between spaces get the construction of their IFC material
  layer set, or a default construction.

The generated model is always built from the configuration written by `ifctrano config`, so that the configuration
describes exactly the simulated building.

## Checking the physics

`tests/physics.py` reads the parameters driving the simulation (zone geometry, envelope areas, orientations and
constructions, nominal values of the heating components) from the generated Buildings model. The tests compare them
with snapshots, so that a change of ifctrano or trano cannot silently change the physics of the models.
