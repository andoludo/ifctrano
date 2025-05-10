import random
import re
import string
import uuid
from typing import get_args

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


def generate_alphanumeric_uuid() -> str:
    return str(uuid.uuid4().hex).lower()


def _round(value: float) -> float:
    return round(value, ROUNDING_FACTOR)


def get_building_elements(ifcopenshell_file: file) -> list[entity_instance]:
    return [
        e
        for building_element in get_args(BuildingElements)
        for e in ifcopenshell_file.by_type(building_element)
    ]
