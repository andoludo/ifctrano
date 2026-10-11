"""Physical parameters of a generated Buildings model.

The Modelica text produced by trano changes with its templates (layout, record
names, how parameters are grouped), while the physics must not. This module
reads the parameters that drive the simulation (zone geometry, envelope areas,
orientations and constructions, nominal values of the heating components) into
a canonical form that can be compared between trano versions.
"""

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator, Optional

ZONE = re.compile(r"Buildings\.ThermalZones\.Detailed\.MixedAir\s+(\w+)\s*\(")
CONSTRUCTION = re.compile(
    r"Buildings\.HeatTransfer\.Data\.(?:OpaqueConstructions|GlazingSystems)\.Generic"
    r"\s+(\w+)\s*\("
)
HEATING_COMPONENT = re.compile(
    r"\b((?:radiator|valve|pump|three_way_valve|temperature_sensor|boiler|split_valve"
    r"|(?:boiler|collector|emission|three_way_valve)_control)_\w+)\s*\("
)
ASSIGNMENT = re.compile(r"(\w+)\s*=\s*")
NUMBER = re.compile(r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?$")
TILTS = {"Wall": "wall", "Ceiling": "ceiling", "Floor": "floor"}
AREA_DIGITS = 6
"""Summed areas are rounded to remove the noise of the summation order."""
AREAS = {"area", "window_area"}
AZIMUTH_DIGITS = 2
"""[rad] ifctrano writes azimuths with two decimals."""
CONSTRUCTIONS = {
    "datConExt": "opaque",
    "datConExtWin": "windowed",
    "datConBou": "ground",
    "surBou": "adiabatic",
    "datConPar": "partition",
}


def _closing(text: str, start: int) -> int:
    """Index of the parenthesis closing the one opened at ``start``."""
    depth = 0
    for index in range(start, len(text)):
        if text[index] in "({":
            depth += 1
        elif text[index] in ")}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"Unbalanced parentheses at {start}")


def _arguments(text: str) -> dict[str, str]:
    """Top-level ``name=value`` modifications of a declaration."""
    arguments = {}
    index = 0
    while index < len(text):
        match = ASSIGNMENT.match(text, index)
        if match is None:
            if text[index] in "({":
                index = _closing(text, index)
            index += 1
            continue
        start = match.end()
        end = start
        while end < len(text) and text[end] != ",":
            if text[end] in "({":
                end = _closing(text, end)
            end += 1
        arguments[match.group(1)] = text[start:end].strip()
        index = end + 1
    for name, start in _records(text):
        arguments[name] = text[start + 1 : _closing(text, start)]
    return arguments


def _records(text: str) -> Iterator[tuple[str, int]]:
    """Top-level record modifications ``name( ... )`` and their opening index."""
    depth = 0
    for match in re.finditer(r"(\w+)\s*\(|[(){}]", text):
        if match.group(1) is not None:
            if depth == 0:
                yield match.group(1), match.end() - 1
            depth += 1
        elif match.group(0) in "({":
            depth += 1
        else:
            depth -= 1


def _array(value: str) -> list[str]:
    return [
        item.strip() for item in value.strip().strip("{}").split(",") if item.strip()
    ]


def _declaration(text: str, match: re.Match[str]) -> str:
    start = match.end() - 1
    return text[start + 1 : _closing(text, start)]


def _azimuth(value: float) -> float:
    """Azimuth in (-pi, pi], so that 4.71 and -1.57 compare equal."""
    angle = math.remainder(value, 2 * math.pi)
    if math.isclose(angle, -math.pi, abs_tol=0.01):
        angle = math.pi
    return round(angle, AZIMUTH_DIGITS) + 0.0


def _surfaces(kind: str, record: str) -> list[dict[str, Any]]:
    arguments = _arguments(record)
    areas = [float(area) for area in _array(arguments["A"])]
    tilts = [TILTS[tilt.rsplit(".", 1)[-1]] for tilt in _array(arguments["til"])]
    # Adiabatic surfaces (surBou) have no layers.
    layers: list[Optional[str]] = list(_array(arguments.get("layers", "")))
    layers += [None] * (len(areas) - len(layers))
    azimuths = [float(azimuth) for azimuth in _array(arguments.get("azi", ""))]
    surfaces = []
    for index, (area, tilt, layer) in enumerate(zip(areas, tilts, layers)):
        surface: dict[str, Any] = {"kind": kind, "tilt": tilt, "layers": layer}
        # The orientation of horizontal surfaces does not change their physics.
        if tilt == "wall" and azimuths:
            surface["azimuth"] = _azimuth(azimuths[index])
        surface["area"] = area
        if kind == "windowed":
            surface["glazing"] = _array(arguments["glaSys"])[index]
            surface["window_area"] = float(_array(arguments["wWin"])[index]) * float(
                _array(arguments["hWin"])[index]
            )
        surfaces.append(surface)
    return surfaces


def _merge(surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Surfaces summed per kind, orientation and construction, in a stable order."""
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for surface in surfaces:
        key = tuple(
            (name, value)
            for name, value in sorted(surface.items())
            if name not in AREAS
        )
        total = merged.setdefault(key, {**dict(key), "area": 0.0})
        total["area"] += surface["area"]
        if "window_area" in surface:
            total["window_area"] = (
                total.get("window_area", 0.0) + surface["window_area"]
            )
    for total in merged.values():
        total["area"] = round(total["area"], AREA_DIGITS)
        if "window_area" in total:
            total["window_area"] = round(total["window_area"], AREA_DIGITS)
    return [merged[key] for key in sorted(merged, key=json.dumps)]


def zones(model: str) -> dict[str, dict[str, Any]]:
    """Geometry and envelope of each thermal zone."""
    result = {}
    for match in ZONE.finditer(model):
        arguments = _arguments(_declaration(model, match))
        surfaces = [
            surface
            for record, kind in CONSTRUCTIONS.items()
            if record in arguments
            for surface in _surfaces(kind, arguments[record])
        ]
        result[match.group(1)] = {
            "height": float(arguments["hRoo"]),
            "floor_area": round(float(arguments["AFlo"]), AREA_DIGITS),
            "surfaces": _merge(surfaces),
        }
    return result


def heating(model: str) -> dict[str, dict[str, float]]:
    """Numerical parameters of the heating components and their controls."""
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for match in HEATING_COMPONENT.finditer(model):
        if match.group(1) in result:
            continue
        for name, value in _arguments(_declaration(model, match)).items():
            if NUMBER.match(value):
                result[match.group(1)][name] = float(value)
    return {
        name: dict(sorted(values.items())) for name, values in sorted(result.items())
    }


def _value(value: str) -> float | list[Any] | None:
    """Numbers, arrays and records of a modification; ``None`` for anything else."""
    value = value.removeprefix("final ").strip()
    if NUMBER.match(value):
        return float(value)
    if value.startswith("{"):
        items = []
        index = 1
        while index < len(value) - 1:
            record = re.compile(r"\s*([\w.]+)\s*\(").match(value, index)
            if record is None:
                break
            end = _closing(value, record.end() - 1)
            items.append(_numbers(value[record.end() : end]))
            index = end + 1
            while index < len(value) and value[index] in " ,\n":
                index += 1
        if items:
            return items
        numbers = [_value(item) for item in _array(value)]
        return numbers if all(isinstance(n, float) for n in numbers) else None
    return None


def _numbers(text: str) -> dict[str, Any]:
    arguments = {
        name.removeprefix("final "): _value(value)
        for name, value in _arguments(text).items()
    }
    return {
        name: value for name, value in sorted(arguments.items()) if value is not None
    }


def constructions(model: str) -> dict[str, dict[str, Any]]:
    """Layers of the opaque constructions and glazing systems, by name."""
    return {
        match.group(1): _numbers(_declaration(model, match))
        for match in CONSTRUCTION.finditer(model)
    }


def physics(model: str) -> dict[str, Any]:
    return {
        "zones": zones(model),
        "constructions": constructions(model),
        "heating": heating(model),
    }


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def dump(physics_: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(physics_, indent=2, sort_keys=True) + "\n")
