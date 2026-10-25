"""!
@file conftest.py
@brief Shared pytest fixtures: import paths and a throwaway certificate set.
@details Certificates come from tools/make-certs.sh, so every test run also checks that the
         script a user runs still works (John, 2026-10-11: key generation is part of the test cycle).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

## Repository root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "client"))
sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture(scope="session")
def certs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """!
    @brief Make a fresh certificate set once per test run (EC keys, short validity).
    @return The output folder (has ca/, wifiterm/, localhost/, bad/).
    """
    if not shutil.which("openssl"):
        pytest.skip("openssl not installed")
    out = tmp_path_factory.mktemp("certs") / "certs"
    subprocess.run(
        ["bash", str(ROOT / "tools" / "make-certs.sh"), "-o", str(out), "-d", "30"],
        check=True,
        capture_output=True,
    )
    return out


@pytest.fixture(scope="session")
def signing(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """!
    @brief Make a throwaway firmware signing key with tools/make-signing-key.sh (NOTES I-25).
    @return Folder with fw-sign.key and fw-sign.pub.
    """
    if not shutil.which("openssl"):
        pytest.skip("openssl not installed")
    out = tmp_path_factory.mktemp("signing") / "signing"
    subprocess.run(["bash", str(ROOT / "tools" / "make-signing-key.sh"), "-o", str(out)],
                   check=True, capture_output=True)
    return out


def signed_image(signing: Path, folder: Path, text: str, size: int = 5000) -> Path:
    """!
    @brief A test firmware image (0xE9 + "MOCKFW <version>...") signed with tools/sign-fw.sh.
    @param signing Output of the signing fixture. @param folder Where to write.
    @param text Rest of the first line, e.g. "MOCKFW 0.3.0" or "MOCKFW 0.3.0 broken".
    @param size Image size in bytes.
    @return The image path; its .sig is next to it.
    """
    body = b"\xe9" + text.encode() + b"\n"
    img = folder / "wifiterm.bin"
    img.write_bytes(body + bytes(i % 251 for i in range(size - len(body))))
    subprocess.run(["bash", str(ROOT / "tools" / "sign-fw.sh"), str(img), "-k", str(signing / "fw-sign.key")],
                   check=True, capture_output=True)
    return img
