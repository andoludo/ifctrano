import sys
from pathlib import Path

QUESTION = """
Give a general description and parameters description. Don't be verbose.
Be to the point of the following code snippet. Format it in markdown as such:
**General Description**: ....
**Parameters Description**:

    - ....

    - ....
"""

QUESTION_CONFIG_BEFORE = """
Explain what kind of building is described in the following configuration.
Be succinct and to the point and stay with the fact:
"""

sys.path.append(str(Path(__file__).parents[2]))
from docs_src.utils import (  # noqa: E402
    CleanedText,
    DisplayObject,
    Tutorial,
    DisplayImage,
)

tutorial_path = Path(__file__).parents[2].joinpath("tests", "tutorials")
TUTORIALS = [
    Tutorial(
        title="Two zones model",
        contents=[
            CleanedText(
                content="""This tutorial demonstrates how to generate a modelica 
                model and open it with OpenModelica for the two zone BIM model displayed below"""
            ),
            DisplayImage(title="Generated model", path="./img/two_zones_1.png"),
            DisplayImage(title="Generated model", path="./img/two_zones_2.png"),
            CleanedText(
                content="""The file is available in the tests folder of the repository."""
            ),
            DisplayObject(
                language="python",
                object="""
from ifctrano.building import Building
building = Building.from_ifc(path_to_ifc_file)
building.show()
building.save_model()
                """,
            ),
            CleanedText(
                content="""The code snippet above will create a modelica model of the ifc model in the same 
                folder as the ifc file. The model can then be opened in openModelica as shown below when 
                open in OpenModelica. The line `building.show()` will display the generated space boundary of the spaces
                as shown in the figure below."""
            ),
            DisplayImage(title="Space boundary", path="./img/two_zones_4.png"),
            CleanedText(
                content="""ifctrano can also be run using the command line interface as shown below."""
            ),
            CleanedText(
                content="""The help command can be run to see the available options."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create --help",
            ),
            CleanedText(
                content="""To create a model, the following command can be run."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc",
            ),
            CleanedText(
                content="""To display the generated space boundaries along with the 
                Modelica model, the following command can be run."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc --show-space-boundaries",
            ),
            CleanedText(
                content="""This command will display the space boundary as displayed in the figure above."""
            ),
            CleanedText(
                content="""The generated model as shown in the figure below can be opened in openModelica 
                given that the relevant libraries are loaded. By default, ifctrano uses the Buildings library. 
                The model can be opened in OpenModelica using the following command."""
            ),
            DisplayImage(title="Generated model", path="./img/two_zones_3.png"),
            CleanedText(
                content="""Provided that Docker is installed on the host computer, ifctrano can directly 
                simulate the model using the following command."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc --show-space-boundaries --simulate-model",
            ),
            CleanedText(
                content="""Provided that the simulation is successful, the results will be saved locally and a 
                html report will be automatically generated displaying important KPIs, as shown in the figure below."""
            ),
            DisplayImage(title="Simulation report", path="./img/two_zones_5.png"),
        ],
    ),
    Tutorial(
        title="Use different libraries",
        contents=[
            CleanedText(
                content="""By default, ifctrano uses the Buildings library. However, ifctrano can be used 
                with other libraries as well. The following example shows how to use other 
                Modelica libraries with ifctrano.
                ifctrano can generate energy models using the following detailed libraries Buildings,
                 IDEAS as well as reduced order libraries the reduced order model from the AIXLib library
                  and the ISO 13790 library from the buildings library. The following example shows how 
                  to use the IDEAS library with ifctrano."""
            ),
            DisplayObject(
                language="python",
                object="""
from ifctrano.building import Building
building.save_model(library="IDEAS")
                """,
            ),
            CleanedText(
                content="""From the command line, the library can be specified using the `--library` option. 
                The following command will generate a model using the IDEAS library."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc --library IDEAS",
            ),
            CleanedText(
                content="""ifctrano will rebuild the model using the IDEAS library as shown below. 
                The generated model can be opened in OpenModelica as shown below when open in OpenModelica."""
            ),
            DisplayImage(title="Generated model", path="./img/two_zones_6.png"),
        ],
    ),
    Tutorial(
        title="Many zones model",
        contents=[
            CleanedText(
                content="""This tutorial demonstrates how to generate a modelica 
                model and open it with OpenModelica for multizone BIM model displayed below"""
            ),
            DisplayImage(title="Generated model", path="./img/multizone_1.png"),
            DisplayImage(title="Generated model", path="./img/multizone_2.png"),
            CleanedText(
                content="""The file is available in the tests folder of the repository."""
            ),
            DisplayObject(
                language="python",
                object="""
from ifctrano.building import Building
building = Building.from_ifc(path_to_ifc_file)
building.save_model()
                """,
            ),
            CleanedText(
                content="""The code snippet above will create a modelica model of the ifc model in the same 
                folder as the ifc file. The model can then be opened in openModelica."""
            ),
            DisplayImage(title="Generated model", path="./img/multizone_5.png"),
            CleanedText(
                content="""To display the generated space boundaries along with the Modelica model and simulate 
                at the same time using the command line, one can use the following command."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc --show-space-boundaries --simulate-model",
            ),
            CleanedText(
                content="""The generated space boundaries will be displayed as shown in the figure below."""
            ),
            DisplayImage(title="Space boundaries", path="./img/multizone_3.png"),
            CleanedText(
                content="""The simulation output will be automatically opened."""
            ),
            DisplayImage(title="Space boundaries", path="./img/multizone_4.png"),
        ],
    ),
    Tutorial(
        title="Realistic model",
        contents=[
            CleanedText(
                content="""This tutorial demonstrates how ifctrano handles realistic BIM models.
                This example is based on the duplex appartment model available online. 
                The model is a realistic model of a duplex apartment with two floors and multiple 
                rooms as shown in the figures below."""
            ),
            DisplayImage(title="Generated model", path="./img/duplex_1.png"),
            DisplayImage(title="Generated model", path="./img/duplex_2.png"),
            CleanedText(
                content="""The file is available in the tests folder of the repository. And the command line 
                interface can be used to generate the model as shown below (similar to the previous tutorials)."""
            ),
            DisplayObject(
                language="python",
                object="""
from ifctrano.building import Building
building = Building.from_ifc(path_to_ifc_file)
building.save_model()
                """,
            ),
            CleanedText(
                content="""The code snippet above will create a modelica model of the ifc model in the same 
                folder as the ifc file. The model can then be opened in openModelica."""
            ),
            DisplayImage(title="Generated model", path="./img/duplex_6.png"),
            CleanedText(
                content="""To display the generated space boundaries along with the Modelica 
                model and simulate at the same time using the command line, one can use the following command."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc --show-space-boundaries --simulate-model",
            ),
            CleanedText(
                content="""The generated space boundaries will be displayed as shown in the figure below."""
            ),
            DisplayImage(title="Space boundaries", path="./img/duplex_3.png"),
            CleanedText(
                content="""The simulation output will be automatically opened on your local browser."""
            ),
            DisplayImage(title="Space boundaries", path="./img/duplex_4.png"),
        ],
    ),
]


def gen_docs() -> None:
    for tutorial in TUTORIALS:
        tutorial.write(
            Path(__file__)
            .parents[2]
            .joinpath("docs", "tutorials", f"{tutorial.name()}.md")
        )


if __name__ == "__main__":
    gen_docs()
