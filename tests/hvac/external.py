"""Open HVAC models downloaded on demand, pinned by commit and SHA-256.

Files are cached in ``tests/models/external`` (git-ignored), so they are only
downloaded once.
"""

import hashlib
import urllib.request
from pathlib import Path

import pytest

CACHE = Path(__file__).parents[1] / "models" / "external"

# RWTH Aachen E3D "DigitalHub" (MIT license), https://github.com/RWTH-E3D/DigitalHub
# The architecture model of the same building is already part of the test
# models (tests/models/space_boundary/FM_ARC_DigitalHub_with_SB_neu.ifc).
DIGITALHUB_COMMIT = "36565d529b4dadeca625de2b793d7e16700171e9"
DIGITALHUB_URL = (
    f"https://raw.githubusercontent.com/RWTH-E3D/DigitalHub/{DIGITALHUB_COMMIT}"
)
DIGITALHUB_HEATING = (
    "Version_1/FM_HZG_DigitalHub_v1.ifc",
    "70a40f5d0782b53ae573b89cca8990f66b54b21229527daddd58e5dc2573fbb6",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(base_url: str, relative_path: str, sha256: str) -> Path:
    """Path to the cached file, downloading and verifying it if needed."""
    target = CACHE / Path(relative_path).name
    if target.exists() and _sha256(target) == sha256:
        return target
    CACHE.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    try:
        urllib.request.urlretrieve(f"{base_url}/{relative_path}", partial)  # noqa: S310
    except OSError as e:
        pytest.skip(f"Cannot download {relative_path}: {e}")
    if (actual := _sha256(partial)) != sha256:
        partial.unlink()
        raise ValueError(f"Checksum mismatch for {relative_path}: {actual}")
    partial.replace(target)
    return target
