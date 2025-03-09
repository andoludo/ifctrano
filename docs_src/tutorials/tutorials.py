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
building.save_model()
                """,
            ),
            CleanedText(
                content="""The code snippet above will create a modelica model of the ifc model in the same 
                folder as the ifc file. The model can then be opened in openModelica as shown below when 
                open in OpenModelica."""
            ),
            CleanedText(
                content="""ifctrano can also be run using the command line interface as shown below."""
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create --help",
            ),
            DisplayObject(
                language="bash",
                object="ifctrano create path_to_ifc_file.ifc",
            ),
            DisplayImage(title="Generated model", path="./img/two_zones_3.png"),
            CleanedText(
                content="""Given that the relevant libraries are loaded the figure above shows the model generated."""
            ),
        ],
    ),
    Tutorial(
        title="Multizone model",
        contents=[
            CleanedText(
                content="""This tutorial demonstrates how to generate a modelica 
                model and open it with OpenModelica for the two zone BIM model displayed below"""
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
                folder as the ifc file. The model can then be opened in openModelica as shown below when 
                open in OpenModelica."""
            ),
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
