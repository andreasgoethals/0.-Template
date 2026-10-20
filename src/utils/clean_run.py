"""Wipe what the previous run produced, so the next one starts clean.

    python -m src.utils.clean_run                        list what is there, delete nothing
    python -m src.utils.clean_run --clean                 delete it
    python -m src.utils.clean_run --clean --processed      ...and the data/processed cache too

Clears the **whole `output/` tree on both storage tiers** — `$VSC_DATA` and project storage — so
one invocation is enough whether you are on a laptop or on the cluster. Off-cluster both tiers
collapse into the repository and it is simply `output/`.

`--processed` additionally clears `data/processed/`, the preprocessing cache. It is separate
because rebuilding that cache can cost far more than re-running the notebooks, so "clean the last
run" should not silently throw it away.

LISTS BY DEFAULT. The two mistakes are not symmetric: a listing you meant as a deletion costs one
more command, and a deletion you meant as a listing costs the run.

NEVER TOUCHES `data/raw/`, `checkpoints/` or library submodules — the inputs are irreplaceable and
the weights are either downloaded or a training run to reproduce.
"""

from __future__ import annotations

import argparse
import os
import stat
from pathlib import Path

from src.utils.paths import outputs_dir, processed_dir, results_dir

#: Tracked so an empty directory survives a clone. Not run output, so never counted or deleted —
#: removing them would leave a fresh clone with nowhere to write.
KEEP = frozenset({".gitkeep", ".gitignore"})


def roots(*, processed: bool = False) -> list[Path]:
    """Every tree to clear. Two `output/` roots on the cluster, one locally, plus the cache.

    The parent of `results_dir()` covers project storage's whole output tree, including
    any extra reports a project placed alongside results.
    """
    found = [outputs_dir()]
    results = results_dir().parent
    if not results.is_relative_to(found[0]):
        found.append(results)
    if processed:
        found.append(processed_dir())
    return found


def inventory(root: Path) -> list[Path]:
    """Validate the entire tree before deletion; refuse links, junctions and unknown roots."""
    root = root.absolute()
    allowed = [p.absolute() for p in roots(processed=True)]
    if root not in allowed:
        raise ValueError(f"Not a cleanup target: {root}")
    def reject_link(path: Path) -> None:
        if path.is_symlink() or (
            path.exists() and getattr(path.lstat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValueError(f"Cleanup refuses linked path: {path}")

    for parent in (root, *root.parents):
        reject_link(parent)
    entries = []
    if root.exists() and not root.is_dir():
        raise ValueError(f"Cleanup target is not a directory: {root}")
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            reject_link(path)
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"Cleanup path escapes target: {path}")
            entries.append(path)
    return entries


def measure(root: Path) -> tuple[int, int]:
    """(files, bytes) under a root, ignoring the structure markers."""
    files = [p for p in inventory(root) if p.is_file() and p.name not in KEEP]
    return len(files), sum(p.stat().st_size for p in files)


def wipe(root: Path) -> int:
    """Delete everything under a root except the structure markers. Returns files removed.

    Two passes, and the order matters: files first, then empty directories bottom-up. That leaves
    exactly the directories holding a tracked `.gitkeep` and removes the per-run ones
    (`figures/<notebook>/`) that do not. An `rmtree` of the subtree would take
    `output/figures/.gitkeep` with it, and the next clone would have nowhere to write.
    """
    entries = inventory(root)
    removed = 0
    for path in entries:
        if path.is_file() and path.name not in KEEP:
            path.unlink()
            removed += 1
    for path in sorted((p for p in entries if p.is_dir()),
                       key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--clean", action="store_true", help="actually delete; default lists only")
    parser.add_argument("--processed", action="store_true",
                        help="also clear data/processed/, the preprocessing cache")
    args = parser.parse_args(argv)

    targets = roots(processed=args.processed)
    total_files = total_bytes = 0
    print("Output from the previous run:\n")
    for root in targets:
        files, size = measure(root)
        total_files += files
        total_bytes += size
        state = f"{files:>6} files  {size / 1e6:>9.1f} MB" if files else "         empty"
        print(f"  {state}  {root}")
        for path in inventory(root):
            if path.is_file() and path.name not in KEEP:
                print(f"    {path}")

    print(f"\nTOTAL: {total_files} files, {total_bytes / 1e9:.2f} GB")
    print("Never touched: data/raw/, checkpoints/, library submodules.")

    if not args.clean:
        if total_files:
            print("\nNothing was deleted. Re-run with --clean to delete.")
        return 0

    print("\nDeleting:")
    for root in targets:
        print(f"  removed {wipe(root):>6} files from {root}")
    print("\nClean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
