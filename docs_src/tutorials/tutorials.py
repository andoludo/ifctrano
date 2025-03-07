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
    CommentCodeObject,
    CommentObject,
    DisplayObject,
    TitleText,
    Tutorial,
    DisplayImage,
)

tutorial_path = Path(__file__).parents[2].joinpath("tests", "tutorials")
TUTORIALS = [
    Tutorial(
        title="Two zones ifc model",
        contents=[
            CleanedText(
                content="""This tutorial will demonstrate how to generate and open the generated modelica model via openModelica"""
            ),
            TitleText(content="Input configuration file"),
            CleanedText(
                content="""The following file describe a simple configuration file describing a one zone building 
                with only the building envelope."""
            ),
            CommentObject(
                question=QUESTION_CONFIG_BEFORE,
                object=tutorial_path.joinpath("first_model.yaml"),
            ),
            DisplayObject(
                language="yaml",
                object=tutorial_path.joinpath("first_model.yaml"),
            ),
            TitleText(content="Generate Modelica model"),
            CommentCodeObject(
                language="python",
                function_name="test_first_model",
                object=tutorial_path.joinpath("test_tutorials.py"),
            ),
            CleanedText(
                content="""The model is generated in the same folder as the configuration file but with the 
                extension .mo.
                For the present case, the model is generated in the file first_model.mo. Provided that the required 
                library such as the
                Buildings library in this case are loaded, the generated model can be opened in OpenModelica. 
                As shown in the figure below. Also, if not specified, Trano uses the Buildings library to generate 
                the model."""
            ),
            DisplayImage(title="Generated model", path="./img/first_simulation_1.jpg"),
            CleanedText(
                content="""If one opens the main building components, the generated components is subdivided into 
                different sub-components
                as shown below. As the configuration file contains only the building envelope information, only the
                envelope sub-component is generated"""
            ),
            DisplayImage(
                title="Building components", path="./img/first_simulation_2.jpg"
            ),
            CleanedText(
                content="""Opening the envelope subcomponents, one can see the different base components and 
                information
                constituting the building envelope model. From this point on, the user can modify the model 
                as needed."""
            ),
            DisplayImage(
                title="Envelope components", path="./img/first_simulation_3.jpg"
            ),
            TitleText(content="Simulate"),
            CleanedText(
                content="""The following code snippet can be used to directly simulate the model after generation.
                The model won't be generated but will be directly simulated within openModelica container."""
            ),
            CommentCodeObject(
                language="python",
                function_name="test_first_simulation",
                object=tutorial_path.joinpath("test_tutorials.py"),
            ),
            CleanedText(
                content="""Once the simulation is completed some key parameters are displayed in a report file such as
                displayed below."""
            ),
            DisplayObject(object=tutorial_path.joinpath("first_simulation.html")),
        ],
    )
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
