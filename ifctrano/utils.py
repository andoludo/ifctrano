import random
import re
import string
from typing import Optional, get_args

from ifcopenshell import file, entity_instance

from ifctrano.base import ROUNDING_FACTOR
from ifctrano.types import BuildingElements


def remove_non_alphanumeric(text: str) -> str:
    text = text.replace(" ", "_")
    return re.sub(r"[^a-zA-Z0-9_]", "", text).lower()


def short_uuid() -> str:
    return "".join(
        random.choices(string.ascii_letters + string.digits, k=3)  # noqa: S311
    )


def modelica_identifier(text: Optional[str], fallback: str) -> str:
    """Lower-case Modelica identifier made from ``text``.

    Modelica identifiers start with a letter: names starting with a digit are
    prefixed, and ``fallback`` (which must be valid) is used for empty names.
    """
    name = remove_non_alphanumeric(text or "")
    if not name:
        return fallback
    if not name[0].isalpha():
        return f"{fallback.split('_')[0]}_{name}"
    return name


def _round(value: float) -> float:
    return round(value, ROUNDING_FACTOR)


def get_building_elements(ifcopenshell_file: file) -> list[entity_instance]:
    return [
        e
        for building_element in get_args(BuildingElements)
        for e in ifcopenshell_file.by_type(building_element)
    ]
