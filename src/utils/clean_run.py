"""Preview or remove disposable run output; retained assets are never part of cleanup.

    python -m src.utils.clean_run                        list what is there, delete nothing
    python -m src.utils.clean_run --clean                 delete it
    python -m src.utils.clean_run --clean --processed      ...and the data/processed cache too

Clears disposable output across experiments on both tiers. Retained results, submission
receipts and workspaces are protected. Scratch needs a separate publication/ownership check.

`--processed` opts into rebuilding the preprocessing cache, which can be expensive.
Listing is default because accidental deletion can lose a run. Raw inputs, weights, runtimes,
reusable caches and library submodules are outside cleanup targets.
"""

from __future__ import annotations

import argparse
import os
import stat
from pathlib import Path

from src.utils.paths import outputs_dir, processed_dir, results_dir

# Preserve tracked directory markers so a fresh clone retains its layout.
KEEP = frozenset({".gitkeep", ".gitignore"})
# Deleting receipts can duplicate submissions; results and resumable work are not disposable.
PROTECTED = frozenset({"results", "submissions", "workspaces"})


def roots(*, processed: bool = False) -> list[Path]:
    """Output roots to inspect, with protected subtrees excluded, plus the opt-in cache.

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
        dirs[:] = [name for name in dirs if name not in PROTECTED]
        for name in dirs + files:
            if name in PROTECTED:
                continue
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
    """Remove files before empty directories, preserving protected subtrees and layout markers."""
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
    print("Protected: results/, submissions/, workspaces/, raw data, checkpoints, runtimes, libraries.")

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
