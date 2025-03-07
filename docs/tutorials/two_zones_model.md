# Two zones model
This tutorial demonstrates how to generate a Modelica model and open it using OpenModelica for the two-zone BIM model displayed below.

![Generated model](./img/two_zones_1.jpg)

![Generated model](./img/two_zones_2.jpg)

The file is located in the `tests` folder of the repository.


```python

from ifctrano.building import Building
building = Building.from_ifc(path_to_ifc_file)
building.save_model()
                
```
            

The code snippet above generates a Modelica model of the IFC file in the same directory as the IFC file. You can then open the model in OpenModelica, as demonstrated below.

![Generated model](./img/two_zones_3.jpg)

Given that the relevant libraries are loaded, the figure above displays the generated model.

