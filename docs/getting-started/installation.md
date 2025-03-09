# Installation
## Optional dependencies

### Graphviz

`ifctrano` utilizes Graphviz to arrange various Modelica components within the model. While installation is not mandatory, it is advisable for improved visualization. 

You can install Graphviz by following the instructions on the [official website](https://graphviz.org/download/). For Windows installation, ensure that the Graphviz `bin` folder is added to the system path.

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
            

ifctrano is a Python package that can be installed via pip.


```bash
pip install ifctrano
```
            

`ifctrano` can also be utilized with Poetry.


```bash
poetry add ifctrano
```
            

To verify the installation, execute the following command in the terminal.


```bash
ifctrano --help
```
            


```bash
ifctrano verify
```
            

