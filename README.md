# {{PROJECT_NAME}}

> {{DESCRIPTION}}

    Author   {{AUTHOR}} <{{EMAIL}}>
    Context  PhD research, KU Leuven — machine learning on tabular data

## What this is

Replace this with what the project does, what it is compared against, and what a result from it
looks like.

## Setup

Windows PowerShell — **one command per line, `&&` is a parser error there**:

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
pip install -e ".[dev]"
```

## Shared library submodules

The template includes **VSC Library only**, at `vsc-library/`. Initialize it after cloning:

```powershell
git submodule update --init -- vsc-library
git submodule status
```

Libraries are independent repositories. Add only those the project needs:

| Library | Repository | Mountpoint |
|---|---|---|
| VSC infrastructure | [VSC Library](https://github.com/andreasgoethals/VSC_Library) | `vsc-library` |
| Tabular foundation models (optional) | [TFM Library](https://github.com/andreasgoethals/TFM_Library) | `tfm-library` |
| Decision models (optional) | [DM Library](https://github.com/andreasgoethals/DM_Library) | `decision-models-library` |

For a project without VSC Library, this is the complete registration example:

```powershell
git submodule add -b main https://github.com/andreasgoethals/VSC_Library.git vsc-library
git add -- .gitmodules vsc-library
git commit --only -m "Add VSC Library reference" -- .gitmodules vsc-library
git push
```

Do not repeat `submodule add` when the path is already registered. For an optional
library, substitute its repository URL and mountpoint from the table. Adding one
library never installs the others. Keep added mountpoints excluded from packaging,
linting and test discovery; the three paths above are already excluded here.

The `.gitmodules` registration records the URL; the committed gitlink records the
exact library revision. Read shared documents and snapshots in place, cite source
paths and symbols, and record the pin beside results that depend on them.

**Consumer copies are read-only.** Never edit, refresh, lint, format or test inside
them. VSC has no local-file exception: put project-specific operations in
`docs/VSC.md`. TFM and DM permit only their ignored `PROJECT_SPECIFIC.md`, created
from their own `PROJECT_SPECIFIC.template.md`. Corrections belong in the canonical
library checkout.

The owner's canonical checkouts live together in the local `0. Literature`
workspace. Its `scripts/maintain.py` runs each library's maintenance in parallel.
After reviewing, committing and pushing library changes, run from that workspace:

```powershell
python scripts/propagate_to_downstream.py --dry-run
python scripts/propagate_to_downstream.py --push
```

Propagation discovers existing consumers through their submodule URLs, including
this template. It pins the exact clean published library commit, commits only the
submodule path and optionally pushes. It never adds an unregistered library.
A new consumer must be inside the searched Projects tree or supplied through
`--root`. The template's daily Dependabot configuration proposes VSC pin updates
on GitHub; proposals require review and merging.

For a single consumer, the local helper reports the current pin by default:

```powershell
python -m src.utils.update_library
python -m src.utils.update_library --library vsc-library --update --commit
git push
```

Review the library changelog before updating. Publishing a library alone does not
change a consumer's committed pin; run propagation or merge an update proposal.

## Running it

```powershell
python -m src.utils.run_notebooks
```

```powershell
python -m src.utils.clean_run
```

Add this project's own entry points here as they appear. On the cluster, see
[`docs/VSC.md`](docs/VSC.md).

---

## Based on the repository template

This repository was created from
[**andreasgoethals/0.-Template**](https://github.com/andreasgoethals/0.-Template).
[`docs/TEMPLATE.md`](docs/TEMPLATE.md) is that template: it explains every folder and file here,
and it is a **starting point, not a contract** — this project may grow past it, and deviating where
the work needs it is fine as long as you say so. Generic rule changes belong at the source above.

*Keep this chapter, at the bottom, in every project that starts from the template. Everything above
it is that project's own.*
