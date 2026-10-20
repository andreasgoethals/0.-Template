"""Inspect or bump one registered library pin; VSC is the default. Reports without changes.

    python -m src.utils.update_library                     local pin and checkout status
    python -m src.utils.update_library --update             fetch and move the working tree
    python -m src.utils.update_library --update --commit    ...and record the new pin
    python -m src.utils.update_library --library tfm-library  select an optional library

WHY THREE STEPS AND NOT ONE: `git submodule update --remote` moves the working tree but
does NOT record the new pin — `git submodule status` then shows a leading `+`, which looks
like an error and is not. The pin only changes once the submodule path is added and
committed. Doing that silently would move the literature a result was checked against
without saying so, which is exactly the thing a pinned submodule exists to prevent.

READ THE SELECTED LIBRARY'S CHANGELOG BEFORE BUMPING. The point of the pin is that a result is
reproducible against the literature as it stood; moving it is a decision, not maintenance.

The updater checks out upstream files at the selected revision; it never edits their content.
It never pushes. With --commit it records only the selected submodule path.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

#: `parents[2]` because this file is `<root>/src/utils/update_library.py`.
REPO_ROOT = Path(__file__).resolve().parents[2]
SUBMODULE = "vsc-library"


def git(*args: str, check: bool = True) -> str:
    """Run git in the repository root and return stdout."""
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def status() -> str:
    """`git submodule status` for our submodule. A leading `+` means tree != pin."""
    for line in git("submodule", "status", SUBMODULE).splitlines():
        if SUBMODULE in line:
            return line.strip()
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--update", action="store_true", help="fetch and move the working tree")
    parser.add_argument("--commit", action="store_true", help="record the new pin (needs --update)")
    parser.add_argument("--library", default="vsc-library",
                        choices=["vsc-library", "tfm-library", "decision-models-library"])
    args = parser.parse_args(argv)
    global SUBMODULE
    SUBMODULE = args.library
    if args.commit and not args.update:
        parser.error("--commit requires --update")
    if not git("ls-files", "-s", "--", SUBMODULE).startswith("160000"):
        print(f"{SUBMODULE} is not registered. See docs/TEMPLATE.md.")
        return 1
    if not (REPO_ROOT / SUBMODULE).exists():
        print(f"{SUBMODULE}/ is missing. Add it with:")
        print(f"  git submodule add <library repo url> {SUBMODULE}")
        return 1

    line = status()
    if line.startswith("-"):
        # A `-` prefix means the submodule is registered but never initialised: the folder
        # exists and is empty, which reads as "the library is missing" if you do not know this.
        print(f"{SUBMODULE}/ is not initialised (empty after a fresh clone). Run:")
        print(f"  git submodule update --init -- {SUBMODULE}")
        return 1

    if args.update:
        if git("diff", "HEAD", "--", ".gitmodules"):
            raise RuntimeError("Publish pending submodule registrations first")
        if git("diff", "--cached", "--", SUBMODULE):
            raise RuntimeError("Preserve the already-staged submodule pin")
        result = subprocess.run(["git", "-C", str(REPO_ROOT / SUBMODULE),
                                 "status", "--porcelain"], capture_output=True, text=True)
        if result.returncode or result.stdout.strip():
            raise RuntimeError("Initialize the submodule and preserve its local changes first")

    print(f"pinned now:  {line}")
    print(f"changelog:   {SUBMODULE}/CHANGELOG.md  <- read this before bumping")

    if not args.update:
        print("\nNothing changed. Re-run with --update to move the working tree.")
        return 0

    print(f"\nfetching upstream and moving {SUBMODULE}/ ...")
    git("submodule", "update", "--remote", SUBMODULE)
    print(f"pinned tree: {status()}")

    if not args.commit:
        print(
            "\nThe working tree moved but THE PIN IS NOT RECORDED — the leading `+` above is\n"
            "that, not an error. To record it:\n"
            f"  git add {SUBMODULE}\n"
            f'  git commit --only -m "Bump {SUBMODULE} pin" -- {SUBMODULE}'
        )
        return 0

    if not git("diff", "--", SUBMODULE) and not git("diff", "--cached", "--", SUBMODULE):
        print("\nAlready up to date — nothing to commit.")
        return 0
    git("add", SUBMODULE)
    # The `-- vsc-library` pathspec is not cosmetic: a bare `git commit` would sweep in
    # whatever else happened to be staged, and this script must only ever move the pin.
    git("commit", "-m", f"Bump {SUBMODULE} pin", "--", SUBMODULE)
    print(f"\npin recorded: {status()}")
    print("Note the new pin in docs/CHANGELOG.md — a result depends on which literature it")
    print("was checked against.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
