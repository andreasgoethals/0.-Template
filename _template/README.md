# Repository template

This repository is the project starting point, with placeholders. All portable rules and
utilities are explained in [docs/TEMPLATE.md](../docs/TEMPLATE.md).

## New project

1. GitHub **Use this template** → new public/private repository; clone it. Use a template,
   not a fork of this public repository, when independent history/private visibility is needed.
2. Fill placeholders:

```powershell
python _template/init_project.py ProjectName --description "One sentence about the project."
```

3. Remove `_template/`. With permission, install the project's dependencies into a local
   environment. Initialize the reference with `git submodule update --init -- vsc-library`.
4. Fill README, project style and VSC/runtime/resource TODOs. Start with experiment-0 validation;
   the synthetic notebook only demonstrates reporting. Optional TFM/DM setup is in TEMPLATE.md.
5. Run `python -m pytest -q`, `python -m ruff check .` and `python -m src.utils.run_notebooks`.

On VSC the Git checkout goes on DATA; environments/images and persistent assets go on PROJECT.
Prefer compact immutable containers. Read the storage/concurrency policy before staging or submitting.

`init_project.py` substitutes project/package/author/date/URL placeholders, validating TOML and
notebook JSON before writing. `--dry-run` previews. It skips libraries/assets/linked directories,
installs nothing, makes no Git changes and deletes nothing. The uninitialized package name is
intentionally not installable. After template edits, test an initialized throwaway copy.

## Existing project

Copy `docs/TEMPLATE.md` into the project and give an agent this prompt:

```text
Read docs/TEMPLATE.md and this project's agent instructions. Compare the existing repository
with the template and propose a compact adoption plan first. Preserve scientific decisions,
valuable outputs, resume paths and source/runtime revisions used by active or queued jobs.
Adopt only useful compatible changes; document deliberate deviations. Never edit reference
submodules. Ask before installs, submissions, migrations or publication unless already authorized.
After approved edits, align docs and run relevant tests; distinguish local checks from VSC validation.
```

Keep the template generic and concise. Submodule maintenance belongs in the canonical libraries;
propagating TEMPLATE.md alone does not migrate downstream code or storage.
