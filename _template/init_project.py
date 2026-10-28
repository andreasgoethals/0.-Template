"""Turn this checkout into a real project. Run it once, right after "Use this template".

    python _template/init_project.py CreditICL
    python _template/init_project.py CreditICL --dry-run
    python _template/init_project.py CreditICL --repo-url https://github.com/me/CreditICL

No copying: this repository already *is* the template, so the whole job is to replace every
`{{PLACEHOLDER}}` in every text file with a real value, and print the steps it deliberately does
not take.

No installs or Git changes; it only reads Git metadata and does not delete `_template/` for you.
Each of those reaches outside this directory or throws files away, so each is printed instead.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

#: `parents[1]`, because this file is `<repo>/_template/init_project.py`.
REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DOC = REPO_ROOT / "docs" / "TEMPLATE.md"

DEFAULT_AUTHOR = "Andreas Goethals"
DEFAULT_EMAIL = "andreas.goethals@kuleuven.be"
DEFAULT_LIBRARY_URL = "https://github.com/andreasgoethals/VSC_Library.git"
GITHUB_OWNER = "andreasgoethals"

#: File types whose text is substituted. The guard is for the day someone adds an image — a
#: binary quietly mangled by a regex surfaces much later. `""` covers dotfiles.
TEXT_SUFFIXES = frozenset(
    {".py", ".md", ".toml", ".yaml", ".yml", ".cff", ".txt", ".ipynb", ".slurm",
     ".sh", ".cfg", ".ini", ""}
)

#: Never touched. `_template/` is about to be deleted, and its own documentation quotes
#: placeholders as examples, which substitution would destroy.
SKIP_DIRS = frozenset({".git", "_template", "tfm-library", "vsc-library", "dm-library", ".venv", "venv", "__pycache__",
                       ".pytest_cache", ".ruff_cache", "output", "data", "runtimes", "cache"})

#: Upper-case names only, never after a `$`: GitHub Actions expressions look like
#: `${{ matrix.python-version }}`, which a naive substitution would destroy.
PLACEHOLDER_RE = re.compile(r"(?<!\$)\{\{([A-Z][A-Z0-9_]*)\}\}")

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def git(*args: str) -> str:
    """Run git and return stdout, or "" on failure. Never raises: this may not be a git checkout
    at all (someone downloaded a zip), and that must not stop the initialiser."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def detected_repo_url() -> str:
    """This checkout's `origin`, as an https URL, or "".

    The default rather than a name-based guess because the new repository is cloned, so `origin`
    is *already* the right answer — including when its name differs from the project name.
    """
    url = git("remote", "get-url", "origin")
    if not url:
        return ""
    # Normalise the SSH form so the value that lands in pyproject.toml is clickable.
    if url.startswith("git@") and ":" in url:
        host, _, path = url.partition(":")
        url = f"https://{host.split('@', 1)[1]}/{path}"
    return url.removesuffix(".git")


def submodule_state() -> tuple[str, str]:
    """(state, advice) for `vsc-library`. Reported, never acted on. Distinguishes the three cases
    that look alike from outside and need different fixes."""
    if not (REPO_ROOT / ".git").exists():
        return "unknown", "not a git checkout yet — `git init`, or clone the new repository"

    gitlink = git("ls-files", "-s", "vsc-library")
    if not gitlink.startswith("160000"):
        return (
            "MISSING",
            f"no submodule pin recorded. Add it once:\n"
            f"       git submodule add {DEFAULT_LIBRARY_URL} vsc-library",
        )
    library = REPO_ROOT / "vsc-library"
    if library.is_dir() and any(library.iterdir()):
        return "populated", "nothing to do"
    return (
        "pinned, empty",
        "the pin came with the repository; initialize the shared VSC guidance:\n"
        "       git submodule update --init -- vsc-library",
    )


def derive(project: str, args: argparse.Namespace) -> dict[str, str]:
    """Every placeholder value, derived from the project name plus the overrides."""
    today = date.today()
    return {
        "PROJECT_NAME": project,
        # Use a lower-case alphanumeric distribution name consistently.
        "PACKAGE_NAME": re.sub(r"[^a-z0-9]", "", project.lower()),
        # Environment-variable prefix, e.g. CREDITICL_STAGING_ROOT.
        "PROJECT_UPPER": re.sub(r"[^A-Z0-9]", "_", project.upper()),
        "AUTHOR": args.author,
        "EMAIL": args.email,
        # One sentence, reused in the README's opening line and pyproject's `description` —
        # so an agent initialises in one command instead of editing two files and getting them
        # slightly different.
        "DESCRIPTION": args.description or f"{project} — PhD research, KU Leuven: machine "
                                           f"learning on tabular data.",
        "YEAR": str(today.year),
        # DD-MM-YYYY: the changelog convention. Not ISO, deliberately — one format everywhere.
        "DATE": today.strftime("%d-%m-%Y"),
        "REPO_URL": args.repo_url or detected_repo_url()
                    or f"https://github.com/{GITHUB_OWNER}/{project}",
    }


def text_files() -> list[Path]:
    """Discover project text without descending into submodules, environments or links."""
    found = []
    submodules = set()
    for line in git("config", "--file", ".gitmodules", "--get-regexp",
                    r"^submodule\..*\.path$").splitlines():
        _, _, value = line.partition(" ")
        if value:
            submodules.add((REPO_ROOT / value).resolve())
    for directory, dirs, files in os.walk(REPO_ROOT, followlinks=False):
        base = Path(directory)
        dirs[:] = [
            name for name in dirs
            if name not in SKIP_DIRS
            and not (base / name).is_symlink()
            and not (
                getattr((base / name).lstat(), "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
            )
            and not (base / name / ".git").exists()
            and not (base / name / "pyvenv.cfg").exists()
            and (base / name).resolve() not in submodules
        ]
        for name in files:
            path = base / name
            if not path.is_symlink() and (
                path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith(".")
            ):
                found.append(path)
    return sorted(found)


def substitute(values: dict[str, str], *, dry_run: bool) -> tuple[list[str], list[str]]:
    """Preflight every replacement before writing. Return (planned files, unknown tokens)."""
    changed: list[str] = []
    leftovers: list[str] = []
    pending: list[tuple[Path, str]] = []
    for path in text_files():
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary despite the name; leave it exactly as it is
        # The template's TOML placeholders occur in basic strings; notebook values
        # occur in JSON strings. Escape their contents rather than inserting raw quotes.
        escaped = (
            {key: json.dumps(value, ensure_ascii=False)[1:-1] for key, value in values.items()}
            if path.suffix.lower() in {".toml", ".ipynb"} else values
        )
        replaced = PLACEHOLDER_RE.sub(
            lambda m, mapping=escaped: mapping.get(m.group(1), m.group(0)), original
        )
        relative = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if replaced != original:
            changed.append(relative)
            if path.suffix.lower() == ".toml":
                tomllib.loads(replaced)
            elif path.suffix.lower() == ".ipynb":
                json.loads(replaced)
            pending.append((path, replaced))
        leftovers += [f"{relative}: {{{{{m.group(1)}}}}}" for m in PLACEHOLDER_RE.finditer(replaced)]
    if not dry_run and not leftovers:
        for path, replaced in pending:
            # Preserve LF: CRLF Slurm scripts fail under bash on the cluster.
            path.write_text(replaced, encoding="utf-8", newline="")
    return changed, leftovers


def next_steps(project: str, values: dict[str, str]) -> str:
    """The steps this script deliberately does not take, because each reaches outside."""
    state, advice = submodule_state()
    return f"""
{"=" * 74}
{project} initialised in {REPO_ROOT}
{"=" * 74}

Nothing was installed, committed, pushed, or deleted. Run these yourself, in order.
Windows PowerShell — ONE COMMAND PER LINE, `&&` is a parser error there.

  1. Delete the template-only folder. It is not part of your project.

     Remove-Item -Recurse -Force _template

  2. Local environment (cluster runtimes go on PROJECT; see docs/VSC.md)

     python -m venv .venv
     .\\.venv\\Scripts\\Activate.ps1
     pip install -e ".[dev]"

  3. VSC Library — READ-ONLY in every project
     state: {state} — {advice}

     Keep project-specific VSC choices in docs/VSC.md.
     Optional TFM/DM libraries: see docs/TEMPLATE.md.

  4. Check it runs.

     python -m pytest -q
     python -m ruff check .
     python -m src.utils.run_notebooks

  5. Make it yours

     README.md          replace everything ABOVE the last chapter. Keep that chapter.
     docs/VSC.md        fill storage/runtime, resources, quotas and publication TODOs.
     scripts/slurm/job.slurm    the same TODOs.
     config/experiment0/        VSC validation configs; replace example.yaml.
     src/visualize/style.py     define this project's shared plotting style.
     notebooks/experiment0/example_analysis.ipynb   replace the synthetic reporting example.
     docs/CHANGELOG.md          add the first project entry dated {values["DATE"]}.

  6. First commit

     git add -A
     git commit -m "Initialise {project} from the repository template"

docs/TEMPLATE.md is a starting point, not a contract. Deviate where the work needs it — but
deliberately, and say so. Generic rule changes belong at the template source.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("project", help="the project name, e.g. CreditICL")
    parser.add_argument(
        "--description", default=None,
        help="one sentence: what the project is and what question it answers. Lands in "
             "README.md and pyproject.toml.",
    )
    parser.add_argument("--author", default=DEFAULT_AUTHOR)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--repo-url", default=None,
                        help="default: this checkout's `origin`, else "
                             f"https://github.com/{GITHUB_OWNER}/<project>")
    parser.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = parser.parse_args(argv)

    if not NAME_RE.match(args.project):
        # The name becomes a storage directory, a distribution name and an
        # environment-variable prefix. A space or a dot fails in one of the three, usually last.
        raise SystemExit(
            f"invalid project name {args.project!r}: start with a letter, then letters, "
            f"digits, '-' or '_' only."
        )
    if not TEMPLATE_DOC.is_file():
        raise SystemExit(f"{TEMPLATE_DOC} is missing — it is the governing document.")
    values = derive(args.project, args)
    print(f"{'DRY RUN — nothing will be written' if args.dry_run else 'initialising'} "
          f"in {REPO_ROOT}\n")
    for key, value in values.items():
        print(f"  {key:<18} {value}")

    changed, leftovers = substitute(values, dry_run=args.dry_run)
    print(f"\n{len(changed)} files {'planned' if args.dry_run or leftovers else 'updated'}:")
    for relative in changed:
        print(f"  {relative}")

    if leftovers:
        # A template bug, not a user error: a key exists that `derive()` does not produce.
        print("\nERROR: unknown placeholders — no files were changed:")
        for item in leftovers:
            print(f"  {item}")

        return 1

    if args.dry_run:
        print("\nDry run. Re-run without --dry-run to apply.")
        return 0

    print(next_steps(args.project, values))
    return 0


if __name__ == "__main__":
    sys.exit(main())
