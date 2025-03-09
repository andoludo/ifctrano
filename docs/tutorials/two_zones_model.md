# Two zones model
This tutorial demonstrates how to generate a Modelica model and open it with OpenModelica for the two-zone BIM model shown below.

![Generated model](./img/two_zones_1.png)

![Generated model](./img/two_zones_2.png)

The file is located in the repository's tests folder.


```python

from ifctrano.building import Building
building = Building.from_ifc(path_to_ifc_file)
building.save_model()
                
```
            

The code snippet above creates a Modelica model of the IFC file in the same directory. You can open the model in OpenModelica as demonstrated below.

Ifctrano can also be executed via the command line interface, as demonstrated below.


```bash
ifctrano create --help
```
            


```bash
ifctrano create path_to_ifc_file.ifc
```
            

![Generated model](./img/two_zones_3.png)

Given that the relevant libraries are loaded, the figure above displays the generated model.

