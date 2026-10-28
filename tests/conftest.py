"""Run offline tests with isolated storage, source imports and headless figures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Fresh clones should not require an editable install to test source imports.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _headless_matplotlib() -> None:
    """Force the Agg backend. A compute node has no display, and the default backend either
    fails there or opens a window that blocks the run."""
    import matplotlib

    matplotlib.use("Agg", force=True)


@pytest.fixture
def isolated_output(tmp_path, monkeypatch):
    """Exercise DATA/PROJECT/SCRATCH branches without touching real cluster storage."""
    from src.utils import paths

    monkeypatch.setenv("VSC_DATA", str(tmp_path / "vsc_data"))
    monkeypatch.setenv(paths.STAGING_ENV_VARS[0], str(tmp_path / "staging"))
    monkeypatch.setenv("VSC_SCRATCH", str(tmp_path / "scratch"))
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_storage_environment(monkeypatch):
    # Tests on VSC must never inherit real asset roots from the submission environment.
    from src.utils import paths

    for key in (*paths.PROJECT_ENV_VARS, *paths.STAGING_ENV_VARS, "VSC_DATA", "VSC_HOME",
                "VSC_SCRATCH", "VSC_SCRATCH_NODE", "VSC_SCRATCH_GPFS1", "VSC_SCRATCH_LUSTRE1"):
        monkeypatch.delenv(key, raising=False)
