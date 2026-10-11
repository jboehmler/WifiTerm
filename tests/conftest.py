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
