"""Repo-relative locally; DATA checkout, persistent PROJECT assets, disposable SCRATCH on VSC.

Configure a shared PROJECT root; the project name is appended. No large-asset fallback to DATA.
Filesystem suitability and quotas need cluster validation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

PROJECT_NAME = "{{PROJECT_NAME}}"
REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ENV_VARS = ("{{PROJECT_UPPER}}_PROJECT_ROOT", "VSC_PROJECT_ROOT")
# Accept existing configuration without silently moving a project's assets.
STAGING_ENV_VARS = ("{{PROJECT_UPPER}}_STAGING_ROOT", "VSC_STAGING_ROOT")


def on_vsc() -> bool:
    return bool(os.environ.get("VSC_DATA"))


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value).expanduser()
    if on_vsc() and not path.is_absolute():
        raise ValueError(f"{name} must be absolute on VSC.")
    return path if path.is_absolute() else REPO_ROOT / path


def staging_override() -> Path | None:
    for name in (*PROJECT_ENV_VARS, *STAGING_ENV_VARS):
        if path := _env_path(name):
            return path
    return None


def project_root() -> Path:
    """Configured persistent storage, never DATA/HOME/SCRATCH on the cluster."""
    root = staging_override()
    if not on_vsc():
        return root or REPO_ROOT
    if root is None:
        raise ValueError(f"Set {PROJECT_ENV_VARS[0]} or VSC_PROJECT_ROOT to allocated PROJECT storage.")
    resolved = root.resolve()
    protected = [REPO_ROOT, *filter(None, (_env_path(key) for key in (
        "VSC_DATA", "VSC_HOME", "VSC_SCRATCH", "VSC_SCRATCH_NODE",
        "VSC_SCRATCH_GPFS1", "VSC_SCRATCH_LUSTRE1",
    )))]
    for path in protected:
        other = path.resolve()
        if resolved.is_relative_to(other) or other.is_relative_to(resolved):
            raise ValueError(f"PROJECT must be separate from checkout/DATA/HOME/SCRATCH: {root}")
    return root


def staging_root() -> Path:
    """Compatibility name for project_root(); not a temporary staging area."""
    return project_root()


def data_root() -> Path:
    return _env_path("VSC_DATA") or REPO_ROOT


def scratch_root() -> Path:
    """Native disposable scratch; never quietly substitute DATA."""
    root = _env_path("VSC_SCRATCH_NODE") or _env_path("VSC_SCRATCH")
    if on_vsc() and root is None:
        raise ValueError("VSC_SCRATCH_NODE or VSC_SCRATCH is required for disposable work.")
    return root or REPO_ROOT / "output" / "workspaces"


def _relative_parts(name: str) -> tuple[str, ...]:
    parts = tuple(name.split("/"))
    if any(p in {"", ".", ".."} for p in parts) or "\\" in name or ":" in name:
        raise ValueError("Use a relative identifier with / separators and no traversal.")
    return parts


def _contained(root: Path, *parts: str) -> Path:
    folder = root.joinpath(*parts)
    # Figure cleanup must not follow a link into another notebook's files.
    if (not folder.resolve().is_relative_to(root.resolve())
            or folder.resolve() != root.resolve().joinpath(*parts)):
        raise ValueError("Path escapes its location through a link.")
    return folder


def _under(root: Path, *parts: str) -> Path:
    return root.joinpath(*parts) if root == REPO_ROOT else root.joinpath(PROJECT_NAME, *parts)


def _asset(*parts: str) -> Path:
    root = project_root()
    return _contained(root, *(() if root == REPO_ROOT else (PROJECT_NAME,)), *parts)


def outputs_dir(experiment: str | None = None) -> Path:
    """Compact DATA reports/logs; retained numerical results use results_dir()."""
    root = _under(data_root(), "output") if on_vsc() else REPO_ROOT / "output"
    return _contained(root, *_relative_parts(experiment)) if experiment is not None else root


def results_dir(*parts: str, experiment: str | None = None) -> Path:
    prefix = _relative_parts(experiment) if experiment is not None else ()
    return _asset("output", *prefix, "results", *parts)


def logs_dir(experiment: str | None = None) -> Path:
    return outputs_dir(experiment) / "logs"


def manifests_dir(experiment: str | None = None) -> Path:
    return outputs_dir(experiment) / "manifests"


def figures_dir(notebook: str | None = None) -> Path:
    """Mirror the relative notebook parent, then figures/<stem>; flat notebooks also work."""
    if notebook is None:
        return outputs_dir() / "figures"
    *parents, stem = _relative_parts(notebook)
    return _contained(outputs_dir(), *parents, "figures", stem)


def captions_path() -> Path:
    return outputs_dir() / "CAPTIONS.md"


def all_results_path() -> Path:
    return outputs_dir() / "All_Results.md"


def raw_dir(*parts: str) -> Path:
    return _asset("data", "raw", *parts)


def processed_dir(*parts: str) -> Path:
    return _asset("data", "processed", *parts)


def checkpoints_dir(*parts: str) -> Path:
    return _asset("checkpoints", *parts)


def runtimes_dir(*parts: str) -> Path:
    """Versioned SIF images or unpacked project environments, outside Git."""
    return _asset("runtimes", *parts)


def cache_dir(*parts: str) -> Path:
    """Reusable caches; temporary caches belong in workspace_dir()."""
    return _asset("cache", *parts)


def workspace_dir(run_id: str) -> Path:
    root = _under(scratch_root()) if on_vsc() else scratch_root()
    return _contained(root, *_relative_parts(run_id))


def data_search_paths(*parts: str) -> list[Path]:
    staged = _asset("data", *parts)
    local = REPO_ROOT.joinpath("data", *parts)
    # A stale DATA copy must not silently substitute for authoritative PROJECT inputs.
    return [staged] if on_vsc() or staged == local else [local, staged]


def find_input(*parts: str) -> Path | None:
    return next((p for p in data_search_paths(*parts) if p.exists()), None)


def config_path(name: str) -> Path:
    return REPO_ROOT / "config" / f"{name.removesuffix('.yaml')}.yaml"


def notebooks_dir() -> Path:
    return REPO_ROOT / "notebooks"


def library_dir(name: str = "vsc-library") -> Path:
    if name not in {"vsc-library", "tfm-library", "dm-library"}:
        raise ValueError(f"Unknown library mountpoint: {name}")
    return REPO_ROOT / name


def repo_dir_on_cluster() -> Path:
    return _under(data_root())


def ensure(path: Path) -> Path:
    (path.parent if path.suffix else path).mkdir(parents=True, exist_ok=True)
    return path


def resolve_writable(preferred: Path) -> Path:
    """Probe the destination; fail rather than redirect large writes into DATA."""
    preferred.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=preferred) as probe:
        probe.write(b"ok")
        probe.flush()
    return preferred


def describe() -> dict[str, str]:
    return {"project": PROJECT_NAME, "on_vsc": str(on_vsc()), "repo_root": str(REPO_ROOT),
            **{f.__name__: str(f()) for f in (
                project_root, data_root, scratch_root, outputs_dir, results_dir, runtimes_dir,
            )}}
