import ast
import os
from pathlib import Path
from typing import List, Optional, Union

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()


class Text(BaseModel):
    content: str

    def write(self) -> str:
        return self.content


class TitleText(Text):
    tag: str = "##"

    def write(self) -> str:
        return f"{self.tag} {self.content}"


class CleanedText(Text):
    def write(self) -> str:
        return _clean_text(self.content)


class DisplayObject(BaseModel):
    object: Union[Path, str]
    language: Optional[str] = None

    def write(self) -> str:
        object = (
            self.object if isinstance(self.object, str) else self.object.read_text()
        )
        if self.language:
            return f"""
```{self.language}
{object}
```
            """
        return object


class DisplayImage(BaseModel):
    title: str
    path: Union[Path, str]

    def write(self) -> str:
        return f"""![{self.title}]({self.path})"""


class CommentObject(BaseModel):
    question: str
    object: Path

    def write(self) -> str:
        return _ai_assistant(f"{self.question}:{self.object.read_text()}")


class CommentCodeObject(CommentObject):
    language: str
    function_name: str
    question: str = """
Give a general explanation of the code snippet and a general description and parameters
description (as bullet points). Don't be verbose.
Be to the point and do not repeat or rewrite the code snippet. Format as markdown.
And if have to use title tags, use tags "###" or "####".
"""

    def write(self) -> str:
        code_snippet = extract_function_snippet(self.object, self.function_name)
        return f"""
```{self.language} title='{self.object.stem.replace("_", " ").capitalize()}'
{code_snippet}
```
{_ai_assistant(f"{self.question}:{code_snippet}")}
"""


class Tutorial(BaseModel):
    title: str
    contents: List[
        Union[
            Text,
            TitleText,
            CleanedText,
            CommentObject,
            CommentCodeObject,
            DisplayObject,
            DisplayImage,
        ]
    ]

    def build(self) -> str:
        output = f"# {self.title}\n"
        for content in self.contents:
            output += f"{content.write()}\n\n"
        return output

    def write(self, destination_path: Path) -> None:
        destination_path.write_text(self.build())

    def name(self) -> str:
        return self.title.replace(" ", "_").lower()


def extract_function_snippet(file_path: Path, function_name: str) -> Optional[str]:
    file_content = file_path.read_text()
    tree = ast.parse(file_content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            start_line = node.body[0].lineno
            end_line = node.body[-1].end_lineno
            with open(file_path) as f:
                lines = f.readlines()[start_line - 1 : end_line]
            function_text = "".join(lines)
            return function_text
    return None


def _ai_assistant(question: str) -> str:
    if not question:
        return ""
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "user", "content": f"{question}"},
        ],
        model="gpt-4o-mini",
    )
    return chat_completion.choices[0].message.content


def _clean_text(text: str) -> str:
    question = f"""
    fix spelling, improve flow, to the point, reduce redundancy and add software development tone.
    Format it into markdown
    . If there is a link please embed it as a markdown link. DO not add title. Do not add extra information. 
    Just give the answer:
    {text}
    """
    return _ai_assistant(question)
