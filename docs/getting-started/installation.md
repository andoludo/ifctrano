# Installation
## Optional dependencies

### Graphviz

`ifctrano` utilizes Graphviz to position various Modelica components within the model. While installation is not mandatory, it is recommended for improved visualization. 

You can install Graphviz by following the instructions on the [official website](https://graphviz.org/download/). For Windows installations, ensure that the Graphviz `bin` folder is added to the system path.

To install Graphviz on Linux, use the following command:

```bash
sudo apt-get install graphviz
```


```bash

sudo apt update
sudo apt install graphviz
                
```
            

## Python package


!!! warning
    Trano requires python 3.9 or higher and docker to be installed on the system.
            

ifctrano is a Python package that can be installed using pip.


```bash
pip install ifctrano
```
            

Ifctrano can also be used with Poetry.


```bash
poetry add ifctrano
```
            

