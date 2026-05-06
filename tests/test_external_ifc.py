"""Integration tests against publicly available IFC sample files.

Each test downloads a small IFC sample from a well-known open-source IFC
sample collection (cached locally in ``tests/models/external``) and verifies
that ``ifctrano`` can convert it into a Modelica model via ``trano``.

The samples are sourced from:

* ``youshengCode/IfcSampleFiles`` - vendor-neutral and Autodesk Revit exports
  routinely used as IFC test corpora.
* ``andrewisen/bim-whale-ifc-samples`` - synthetic IFC fixtures designed to
  be small, easy to parse, and freely redistributable (MIT licence).

All sample files are plain ISO 10303-21 STEP text (``ISO-10303-21;`` magic
header), so there is no executable content; they are safe to download into
the workspace.

Samples that surface a known unfixed upstream issue are intentionally
omitted from this suite and tracked separately - see ifctrano#14
(AdvancedProject.ifc: ``InvalidBuildingStructureError`` on windows without a
matching host wall).
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

from ifctrano.building import Building
from ifctrano.exceptions import NoIfcSpaceFoundError

EXTERNAL_DIR = Path(__file__).parent / "models" / "external"
DOWNLOAD_TIMEOUT_SECS = 60


@dataclass(frozen=True)
class IfcSample:
    """A downloadable IFC sample used as a test fixture."""

    name: str
    url: str
    description: str


# Samples that should successfully convert into a Modelica model.
PASSING_SAMPLES: list[IfcSample] = [
    IfcSample(
        name="Ifc2x3_Duplex_Architecture.ifc",
        url=(
            "https://raw.githubusercontent.com/youshengCode/IfcSampleFiles/"
            "main/Ifc2x3_Duplex_Architecture.ifc"
        ),
        description=(
            "Autodesk Revit Architecture 2011 IFC2x3 duplex apartment, "
            "21 IfcSpace zones."
        ),
    ),
    IfcSample(
        name="Ifc4_SampleHouse.ifc",
        url=(
            "https://raw.githubusercontent.com/youshengCode/IfcSampleFiles/"
            "main/Ifc4_SampleHouse.ifc"
        ),
        description="Vendor-neutral IFC4 sample house with 4 IfcSpace zones.",
    ),
    IfcSample(
        name="TallBuilding.ifc",
        url=(
            "https://raw.githubusercontent.com/andrewisen/bim-whale-ifc-samples/"
            "main/TallBuilding/IFC/TallBuilding.ifc"
        ),
        description=(
            "Synthetic IFC2x3 tall building with 3 stacked IfcSpace zones, "
            "from the BIM Whale sample collection."
        ),
    ),
]


# Samples that legitimately have no IfcSpace and must raise
# ``NoIfcSpaceFoundError``. They guard against silent regressions in
# input validation.
NO_SPACE_SAMPLES: list[IfcSample] = [
    IfcSample(
        name="Ifc4_BasinFacetedBrep.ifc",
        url=(
            "https://raw.githubusercontent.com/youshengCode/IfcSampleFiles/"
            "main/Ifc4_BasinFacetedBrep.ifc"
        ),
        description="Single basin geometry, no IfcSpace.",
    ),
    IfcSample(
        name="Ifc4_CubeAdvancedBrep.ifc",
        url=(
            "https://raw.githubusercontent.com/youshengCode/IfcSampleFiles/"
            "main/Ifc4_CubeAdvancedBrep.ifc"
        ),
        description="Single cube advanced BRep, no IfcSpace.",
    ),
    # Regression test for a bug discovered while curating these tests:
    # IfcMaterialLayer.Material is OPTIONAL per the IFC schema, but
    # ``Constructions.from_ifc`` previously crashed with
    # ``AttributeError: 'NoneType' object has no attribute 'id'`` whenever a
    # layer had no associated material. ``ifctrano/construction.py`` now
    # falls back to a default material in that case, so loading this file
    # gets past construction parsing and fails (as it should) on the
    # missing IfcSpace.
    IfcSample(
        name="Ifc4_WallElementedCase.ifc",
        url=(
            "https://raw.githubusercontent.com/youshengCode/IfcSampleFiles/"
            "main/Ifc4_WallElementedCase.ifc"
        ),
        description=(
            "Elemented wall with IfcMaterialLayer entries whose Material "
            "attribute is NULL (IFC schema permits this). Regression test "
            "for the construction-parsing crash on optional materials."
        ),
    ),
]


def _download_sample(sample: IfcSample) -> Path:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    dest = EXTERNAL_DIR / sample.name
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        with urllib.request.urlopen(  # noqa: S310 - https URL from sample list
            sample.url, timeout=DOWNLOAD_TIMEOUT_SECS
        ) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        pytest.skip(f"Could not download {sample.url}: {exc}")
    if not payload.startswith(b"ISO-10303-21"):
        pytest.skip(
            f"Downloaded {sample.url} is not a valid IFC STEP file "
            f"(unexpected header)."
        )
    dest.write_bytes(payload)
    return dest


@pytest.fixture(scope="session")
def external_ifc_dir() -> Path:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    return EXTERNAL_DIR


@pytest.mark.parametrize("sample", PASSING_SAMPLES, ids=lambda s: s.name)
def test_external_ifc_to_modelica(sample: IfcSample) -> None:
    """Each sample with at least one IfcSpace must produce a Modelica model."""
    ifc_path = _download_sample(sample)
    building = Building.from_ifc(ifc_path)
    model = building.get_model()
    assert model, f"Empty Modelica model for {sample.name}"
    assert building.space_boundaries, (
        f"No space boundaries detected in {sample.name}"
    )


@pytest.mark.parametrize("sample", NO_SPACE_SAMPLES, ids=lambda s: s.name)
def test_external_ifc_without_spaces_raises(sample: IfcSample) -> None:
    """Files without any IfcSpace must surface ``NoIfcSpaceFoundError``."""
    ifc_path = _download_sample(sample)
    with pytest.raises(NoIfcSpaceFoundError):
        Building.from_ifc(ifc_path)
