from __future__ import annotations

import base64
import logging
import lzma
import os
from pathlib import Path

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


def pytest_sessionstart(session) -> None:
    _decrypt_artifacts(PRIVATE_ARIANE_DATA_DIR)
    _decrypt_artifacts(PRIVATE_COMPASS_DATA_DIR)
