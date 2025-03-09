from pathlib import Path

from docs_src.utils import CleanedText, DisplayObject, TitleText, Tutorial, Text

INSTALLATIONS = [
    Tutorial(
        title="Installation",
        contents=[
            TitleText(content="""Optional dependencies"""),
            CleanedText(
                content="""### Graphviz
                ifctrano uses graphviz to position the different modelica components in the model.
                Although it is not necessary, it is recommended to install graphviz to have a better visualization 
                of the model.
                Graphviz can be installed by following the instructions on the official 
                website(https://graphviz.org/download/).
                For windows install, make sure that the graphviz bin folder is added to the system path."""
            ),
            CleanedText(
                content="""For linux, one can use the following command to install graphviz."""
            ),
            DisplayObject(
                language="bash",
                object="""
sudo apt update
sudo apt install graphviz
                """,
            ),
            TitleText(content="""Python package"""),
            Text(
                content="""
!!! warning
    Trano requires python 3.9 or higher and docker to be installed on the system.
            """
            ),
            CleanedText(
                content="""ifctrano is a python package that can be installed using pip."""
            ),
            DisplayObject(language="bash", object="pip install ifctrano"),
            CleanedText(content="""ifctrano can also be used using poetry."""),
            DisplayObject(language="bash", object="poetry add ifctrano"),
            CleanedText(
                content="""To check the installation, run the following command in the terminal."""
            ),
            DisplayObject(language="bash", object="ifctrano --help"),
            DisplayObject(language="bash", object="ifctrano verify"),
        ],
    )
]


def gen_installation_docs() -> None:
    for installation in INSTALLATIONS:
        installation.write(
            Path(__file__)
            .parents[2]
            .joinpath("docs", "getting-started", f"{installation.name()}.md")
        )


if __name__ == "__main__":
    gen_installation_docs()
