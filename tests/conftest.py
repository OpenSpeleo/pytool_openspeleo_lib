from __future__ import annotations

import base64
import logging
import lzma
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESSIV

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# =============================================================================
# Path Constants
# =============================================================================

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
PRIVATE_DATA_DIR = ARTIFACTS_DIR / "private"

PRIVATE_ARIANE_DATA_DIR = PRIVATE_DATA_DIR / "ariane"
PRIVATE_COMPASS_DATA_DIR = PRIVATE_DATA_DIR / "compass"


# =============================================================================
# Decryption
# =============================================================================

# XZ format magic bytes: 0xFD + "7zXZ" + 0x00
XZ_MAGIC_HEADER = b"\xfd7zXZ\x00"


def _decrypt_artifacts(target_dir: Path) -> None:
    if (key_str := os.environ.get("ARTIFACT_ENCRYPTION_KEY")) is None:
        return

    if not target_dir.exists():
        return

    try:
        key_bytes = base64.urlsafe_b64decode(key_str.encode("ascii"))
        aead = AESSIV(key_bytes)
    except ValueError:
        logger.exception("Invalid AES-SIV key provided.")
        return

    for enc_f in target_dir.rglob(pattern="*.encrypted"):
        with enc_f.open(mode="rb") as f:
            enc_data = f.read()

        try:
            dec_data = aead.decrypt(enc_data, None)
        except Exception:
            logger.exception("Failed to decrypt: `%s`.", enc_f)
            continue

        # Auto-detect and decompress XZ/LZMA compressed data
        if dec_data.startswith(XZ_MAGIC_HEADER):
            dec_data = lzma.decompress(dec_data)

        with (enc_f.parent / enc_f.stem).open(mode="wb") as f:
            f.write(dec_data)


# =============================================================================
# Compass File Discovery Functions
# =============================================================================


def discover_compass_mak_files() -> list[pytest.param]:
    """Discover all Compass MAK files in the private directory.

    Returns:
        List of pytest.param objects for use with @pytest.mark.parametrize
    """
    if not PRIVATE_COMPASS_DATA_DIR.exists():
        return []
    mak_files = sorted(PRIVATE_COMPASS_DATA_DIR.glob("*.mak"))
    return [pytest.param(mak_file, id=mak_file.stem) for mak_file in mak_files]


def discover_compass_with_geojson() -> list[pytest.param]:
    """Discover Compass MAK files that have corresponding GeoJSON baselines.

    Returns:
        List of pytest.param objects with (mak_path, geojson_path) tuples
    """
    if not PRIVATE_COMPASS_DATA_DIR.exists():
        return []
    params = []
    for mak_file in sorted(PRIVATE_COMPASS_DATA_DIR.glob("*.mak")):
        geojson_file = mak_file.with_suffix(".geojson")
        if geojson_file.exists():
            params.append(pytest.param(mak_file, geojson_file, id=mak_file.stem))
    return params


def discover_compass_with_ospl_json() -> list[pytest.param]:
    """Discover Compass MAK files that have corresponding OSPL JSON baselines.

    Returns:
        List of pytest.param objects with (mak_path, json_path) tuples
    """
    if not PRIVATE_COMPASS_DATA_DIR.exists():
        return []
    params = []
    for mak_file in sorted(PRIVATE_COMPASS_DATA_DIR.glob("*.mak")):
        # Look for .ospl.json baseline files
        json_file = mak_file.with_suffix(".ospl.json")
        if json_file.exists():
            params.append(pytest.param(mak_file, json_file, id=mak_file.stem))
    return params


# =============================================================================
# Pre-computed Parameter Lists (for module-level parametrize decorators)
# =============================================================================

# Decrypt artifacts before discovery (must happen at import time, before parametrize)
_decrypt_artifacts(PRIVATE_ARIANE_DATA_DIR)
_decrypt_artifacts(PRIVATE_COMPASS_DATA_DIR)

# Compass file discovery
ALL_COMPASS_MAK_FILES = discover_compass_mak_files()
COMPASS_WITH_GEOJSON = discover_compass_with_geojson()
COMPASS_WITH_OSPL_JSON = discover_compass_with_ospl_json()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def artifacts_dir() -> Path:
    """Return path to test artifacts directory."""
    return ARTIFACTS_DIR


@pytest.fixture
def compass_data_dir() -> Path:
    """Return path to private Compass data directory."""
    return PRIVATE_COMPASS_DATA_DIR


@pytest.fixture
def all_compass_mak_paths() -> list[Path]:
    """Return list of all Compass MAK file paths."""
    if not PRIVATE_COMPASS_DATA_DIR.exists():
        return []
    return sorted(PRIVATE_COMPASS_DATA_DIR.glob("*.mak"))


# =============================================================================
# Session Start Hook
# =============================================================================


def pytest_sessionstart(session) -> None:
    # Note: Decryption is now done at module import time for parametrization
    # This hook is kept for any future session-level setup needs
    pass
