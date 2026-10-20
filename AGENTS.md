# AGENTS.md — {{PROJECT_NAME}}

Instructions for AI agents working in this repository.

## 0. Before you start

1. [`docs/TEMPLATE.md`](docs/TEMPLATE.md) — the layout and rules this project started from.
   **Follow it**, and when you deviate — which is allowed, it is a starting point rather than a
   contract — **say so in your reply**. Never silently.
2. [`docs/AGENTS_MEMORY.md`](docs/AGENTS_MEMORY.md) — the cluster runs already done and the dead
   ends already hit. Reading it is not optional: it is how you avoid resubmitting a configuration
   that failed last month, or spending an hour on a known dead end.
3. [`README.md`](README.md) — what this project actually is.

**If a `_template/` folder still exists**, read [`_template/README.md`](_template/README.md)
first: this is either the un-initialised template or a project where nobody deleted the folder.

## 1. Shared library submodules are read-only

The template includes `vsc-library/`. Projects may independently opt into
`tfm-library/`, `dm-library/`, or additional libraries. See
[`docs/TEMPLATE.md`](docs/TEMPLATE.md#shared-library-submodules) for registration
and update commands. Never assume all projects use all libraries.

Read shared documents and implementation snapshots in place; cite source paths
and symbols rather than snapshot line numbers, and record the pinned commit.
Never edit, refresh, lint, format or test a consumer submodule. VSC has no
exception: project operations belong in `docs/VSC.md`. TFM and DM permit only
their ignored `PROJECT_SPECIFIC.md`, created from the library's template.
Report shared corrections for the canonical checkout in `0. Literature`.

## 2. Never commit data or checkpoints

`data/` holds datasets under varying licences; `checkpoints/` holds multi-hundred-MB weights. Both
are gitignored. Do not `git add -f` them, and do not paste raw rows into commits, issues or docs.

## 3. Verify before you assert

This project's value is careful measurement. If a claim cannot be confirmed from the library, the
upstream source, or a primary reference, **say so** rather than filling the gap plausibly.
Distinguish what a paper *evaluated* from what its code merely *supports*; what a mechanism *can*
represent from how *often* it occurs; a library annotation from the primary source it summarises.

## 4. Do not train, install, or push without asking

Cluster runs cost real VSC credits. Installs change a shared environment. Pushes are
{{AUTHOR}}'s action. Ask first.

## 5. Windows PowerShell 5.1 — no `&&`

No `&&`, no ternary, no `??`. One command per line, or `;` with `if ($?) { ... }`:

```powershell
python -m venv .venv
if ($?) { .\.venv\Scripts\Activate.ps1 }
```

SLURM job scripts are a separate world — bash on Linux, normal POSIX syntax. Keep the two straight.

## 6. Write both logs

Newest first, dates `DD-MM-YYYY`.

- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — every substantive change, one bullet, **as short as
  possible**: what, and why only if it is not obvious. Usually one line; longer only when the change
  genuinely is. The detail belongs in the commit.
- [`docs/AGENTS_MEMORY.md`](docs/AGENTS_MEMORY.md) — two things. **Every cluster run**, one row in
  the table: config, outcome, headline number. And **every failure** that cost more than a couple of
  minutes, four lines: **Tried**, **Result**, **Why**, **Instead** — even when the eventual fix
  worked, because the dead end is the expensive part.

## 7. Notebooks and figures

- A notebook contains **no `def` and no `class`** — logic goes in `src/` — and its **last code
  cell prints a text summary**, section by section, in the notebook's own section order.
- **Never pick a colour or a size.** `src/visualize/style.py` owns both, so every notebook here
  looks the same. Add a new one there, once, not in the notebook.
- Save through `src/visualize/figures.FigureSaver`: **PDF only**, into that notebook's own
  folder, which it clears before drawing. The notebook displays each figure inline.
- Use `style.figsize(style.WIDTH_FULL)` or `WIDTH_HALF`: every figure is drawn at the width it
  will occupy on an **A4** page, and never rescaled afterwards — rescaling carries the text with it.
- Captions are the **paper's** captions: pure description, ready to paste under the figure.

## 8. Say you are done only when it runs

```powershell
python -m pytest -q
```

And `python -m src.utils.run_notebooks` if you touched a notebook or anything under
`src/visualize/`. Nothing runs these for you — no CI, no hook — so run them before you claim
anything is finished.
