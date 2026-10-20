"""Run every notebook in parallel, then rebuild the two summary documents.

    python -m src.utils.run_notebooks                     every notebook in notebooks/
    python -m src.utils.run_notebooks --only exploration  just these, by stem
    python -m src.utils.run_notebooks --summaries-only    rebuild the two .md files only

    output/figures/<notebook>/*.pdf   written by the notebooks themselves
    output/figures/CAPTIONS.md        ONE file, all notebooks, notebook order
    output/All_Results.md             every notebook's printed summary, alphabetical

SEPARATE PROCESSES, NOT THREADS: matplotlib's figure registry is global, so two notebooks in
one interpreter would capture each other's figures — silently, giving plausible figures
attributed to the wrong notebook.

A FLATTENED SCRIPT, NOT A JUPYTER KERNEL: nothing extra to install, identical on the cluster,
and a traceback points at a line number instead of a cell index. This lightweight runner rejects
magics except `%matplotlib inline`; notebooks needing them require a Jupyter kernel runner.

THE RUNNER DOES NOT SAVE FIGURES; each notebook does, through `FigureSaver`, so an interactive
*Run All* produces exactly the same PDFs. The runner adds parallelism and the two documents.

NOTEBOOKS ARE DISCOVERED, NOT LISTED, alphabetically — which is also the order in both summary
documents. A hard-coded list silently stops covering a notebook someone added.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from src.utils.atomic import write_text
from src.utils.paths import (
    REPO_ROOT,
    all_results_path,
    captions_path,
    figures_dir,
    notebooks_dir,
)

#: Per-notebook wall-clock limit. A notebook summarises a finished computation; one needing
#: longer is doing work that belongs in a script.
DEFAULT_TIMEOUT = 1800

#: Retained to rebuild reports and preserve unaffected notebooks during partial reruns.
STDOUT_FILE = "_stdout.txt"
FAILURE_FILE = "_failure.txt"


@dataclass
class NotebookResult:
    name: str
    ok: bool
    seconds: float
    n_figures: int
    error: str = ""


def discover(names: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Notebook stems, alphabetical. `names` overrides discovery for a partial rerun."""
    if names:
        for name in names:
            figures_dir(name)  # Validate before constructing input or output paths.
        return tuple(names)
    return tuple(sorted(p.stem for p in notebooks_dir().glob("*.ipynb")))


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _prelude() -> str:
    """Injected above every flattened notebook. `Agg` because a compute node has no display, and
    stdout is captured so `All_Results.md` can be built without the notebook knowing."""
    return (
        "import matplotlib\n"
        'matplotlib.use("Agg")\n'
        "import io as _io\n"
        "from contextlib import redirect_stdout as _redirect\n"
        "_TEXT = _io.StringIO()\n"
    )


def _build_script(nb_path: Path, text_path: Path) -> str:
    """Flatten a notebook's code cells into one script under the capture prelude."""
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    parts = [_prelude(), "\nwith _redirect(_TEXT):\n"]
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"
                  and "".join(c.get("source", [])).strip()]
    if not code_cells:
        raise ValueError("Notebook has no code cells; there is no summary to capture.")
    for i, cell in enumerate(code_cells, start=1):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        # Inline display is harmless headlessly; other magics may change the computation.
        source = re.sub(r"^\s*%matplotlib inline\s*$", "", source, flags=re.M)
        if re.search(r"^\s*[%!]", source, flags=re.M):
            raise ValueError("IPython magics/shell commands require a Jupyter runner.")
        if i == len(code_cells):
            parts.append("    _TEXT.seek(0)\n    _TEXT.truncate(0)\n")
        body = "\n".join(f"    {line}" for line in source.split("\n"))
        parts.append(f"\n    # ---- cell {i} ----\n{body}\n")
    parts.append(
        "\nfrom pathlib import Path as _Path\n"
        "from src.utils.atomic import write_text as _write\n"
        f"_write(_Path({str(text_path)!r}), _TEXT.getvalue())\n"
    )
    return "".join(parts)


def run_one(name: str, timeout: int = DEFAULT_TIMEOUT) -> NotebookResult:
    """Execute one notebook in a fresh process; report execution failures."""
    started = time.time()
    nb_path = notebooks_dir() / f"{name}.ipynb"
    out_dir = figures_dir(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / STDOUT_FILE
    failure_path = out_dir / FAILURE_FILE
    text_path.unlink(missing_ok=True)
    write_text(failure_path, "Run incomplete; no current successful summary.")
    if not nb_path.is_file():
        write_text(failure_path, f"{nb_path} not found")
        return NotebookResult(name, False, 0.0, 0, f"{nb_path} not found")

    # The generated script goes to the system temp dir, NOT into the figure folder: the
    # notebook clears that folder as its first act, and on Windows a directory cannot be
    # modified while it holds the script currently being executed from it.
    try:
        with tempfile.TemporaryDirectory(prefix="notebook_") as directory:
            tmp = Path(directory) / "run.py"
            script = f"import sys\nsys.path.insert(0, {str(REPO_ROOT)!r})\n"
            tmp.write_text(script + _build_script(nb_path, text_path), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(tmp)], cwd=str(REPO_ROOT),
                capture_output=True, text=True, timeout=timeout, check=False,
            )
    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
        write_text(failure_path, str(exc))
        return NotebookResult(name, False, time.time() - started, 0, str(exc))

    n_figs = len(list(out_dir.glob("*.pdf")))
    if proc.returncode != 0:
        # Only the tail: a full traceback from twelve notebooks buries the one that matters.
        tail = "\n".join((proc.stderr or "").strip().splitlines()[-12:])
        write_text(failure_path, tail)
        return NotebookResult(name, False, time.time() - started, n_figs, tail)
    failure_path.unlink(missing_ok=True)
    return NotebookResult(name, True, time.time() - started, n_figs)


# ---------------------------------------------------------------------------
# The two summary documents
# ---------------------------------------------------------------------------


def _captured_text(name: str) -> str:
    failure = figures_dir(name) / FAILURE_FILE
    if failure.exists():
        return "FAILED / INCOMPLETE\n" + failure.read_text(encoding="utf-8")
    path = figures_dir(name) / STDOUT_FILE
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def write_captions(notebooks: tuple[str, ...]) -> Path:
    """ONE CAPTIONS.md for the project, grouped per notebook, in notebook order.

    Built from each `_figures.json`, so it regenerates from disk after an interactive run. A
    figure with no caption gets a loud placeholder rather than being skipped — a gap should be
    visible in the document meant to contain it.
    """
    from src.visualize.figures import read_manifest

    lines = [
        "# Figure captions",
        "",
        "Generated by `python -m src.utils.run_notebooks`. Grouped by notebook, figures in",
        "the order that notebook drew them. Caption text is passed to",
        "`FigureSaver.save(..., caption=...)` in the notebook — edits here are overwritten.",
        "",
        "These are the paper's captions: paste one straight under its figure. Pure description",
        "— what is plotted, on what axes, from how much data. No interpretation.",
        "",
        "Figures are PDFs, drawn at the width they will occupy on an A4 page; never rescale one",
        "in the document, because that rescales its text with it.",
        "",
    ]
    for name in sorted(notebooks):
        if (figures_dir(name) / FAILURE_FILE).exists():
            lines += [f"## {name}", "", "_FAILED / INCOMPLETE: figures are not current._", ""]
            continue
        entries = read_manifest(name)
        lines += [f"## {name}", ""]
        if not entries:
            lines += ["_No figures produced._", ""]
            continue
        for e in entries:
            lines.append(f"**{e['stem']}** — `{e['name']}`")
            lines.append("")
            lines.append(e["caption"] or "> MISSING CAPTION. Add one at the `save()` call.")
            lines.append("")
    path = captions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, "\n".join(lines))
    return path


def write_all_results(notebooks: tuple[str, ...]) -> Path:
    """Every notebook's printed summary, concatenated. The shape is fixed:

    one block per notebook, **sorted alphabetically by notebook name**; each block is that
    notebook's printed summary **verbatim**, not a rewrite; and that summary follows the
    notebook's own section order, so the file and the notebook read the same way round.

    Verbatim matters: the moment this file paraphrases, the two disagree and the notebook wins —
    but this file is the one anybody actually reads.
    """
    names = tuple(sorted(notebooks))
    lines = [
        "# All results",
        "",
        "Every notebook's printed summary, verbatim, one block per notebook in alphabetical",
        "order. Each block follows that notebook's own section order.",
        "Generated by `python -m src.utils.run_notebooks`.",
        "",
    ]
    for name in names:
        text = _captured_text(name).strip()
        lines += ["---", "", f"## {name}", "", "```", text or "(no output captured)", "```", ""]
    path = all_results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, "\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# The one entry point
# ---------------------------------------------------------------------------


def run_all(
    notebooks: tuple[str, ...] | None = None,
    max_workers: int | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[NotebookResult]:
    """Run every notebook in parallel, then rebuild both summary documents.

    Rebuilt even when a notebook failed, from whatever the successful ones wrote: a
    half-updated summary beats a stale one, and the failure is reported separately.
    """
    names = discover(notebooks)
    if not names:
        return []
    # Capped at 4: notebooks are numpy-heavy and each already uses several threads, so more
    # workers than this trades parallelism for cache thrashing.
    workers = max_workers or min(len(names), 4)

    results: list[NotebookResult] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one, name, timeout): name for name in names}
        for fut in as_completed(futures):
            results.append(fut.result())

    report_names = tuple(sorted(set(discover()) | set(names)))
    write_captions(report_names)
    write_all_results(report_names)
    return sorted(results, key=lambda r: names.index(r.name))


def summarise(results: list[NotebookResult]) -> str:
    if not results:
        return "No notebooks found in notebooks/."
    lines = ["", "=" * 74, "NOTEBOOK RUN SUMMARY", "=" * 74]
    for r in results:
        lines.append(
            f"  {'OK    ' if r.ok else 'FAILED'} {r.name:<32} "
            f"{r.seconds:6.1f}s  {r.n_figures:2d} figures"
        )
        if not r.ok:
            lines += [f"           {line}" for line in r.error.splitlines()]
    ok = sum(1 for r in results if r.ok)
    lines += [
        "",
        f"{ok}/{len(results)} notebooks OK, {sum(r.n_figures for r in results)} figures",
        f"  figures   -> {figures_dir()}",
        f"  captions  -> {captions_path()}",
        f"  summaries -> {all_results_path()}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point. `--summaries-only` exists because both documents are built from what the notebooks
# left on disk (`_figures.json` and retained final-cell stdout). Interactive saves refresh captions;
# text summaries need a runner execution. No code runs with --summaries-only.
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--only", nargs="+", metavar="STEM", help="notebook stems to run")
    parser.add_argument("--workers", type=int, default=None, help="parallel processes")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds per notebook")
    parser.add_argument("--summaries-only", action="store_true",
                        help="rebuild both documents from disk, run nothing")
    args = parser.parse_args(argv)

    names = discover(tuple(args.only) if args.only else None)
    if not names:
        print("No notebooks found in notebooks/.")
        return 0

    if args.summaries_only:
        print(f"Rebuilding summaries from disk for: {', '.join(names)}")
        print(f"  captions  -> {write_captions(names)}")
        print(f"  summaries -> {write_all_results(names)}")
        return 0

    print(f"Running {len(names)} notebook(s): {', '.join(names)}")
    results = run_all(names, max_workers=args.workers, timeout=args.timeout)
    print(summarise(results))
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
