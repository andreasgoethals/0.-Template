# Agent instructions — {{PROJECT_NAME}}

## Before working

Read `_template/README.md` first if present, then `docs/TEMPLATE.md`,
`docs/AGENTS_MEMORY.md` and `README.md`. The template is a starting point: explain deliberate
deviations. Keep project decisions in project docs; keep instructions and comments concise.

## Boundaries

- VSC Library is included; TFM/DM are optional independent read-only submodules. Read literature,
  guides and implementation snapshots in place; cite paths/symbols and record pins. Never edit,
  refresh, lint, format or test consumer libraries. Only TFM/DM's ignored `PROJECT_SPECIFIC.md`
  is writable; VSC has no exception. Shared fixes belong in canonical `0. Literature` checkouts.
- Never commit datasets, weights, environments, secrets or raw private rows. No force-adding assets.
- Ask before installs, cluster submissions, migrations or pushes unless already authorized.
  Permission to update documentation does not authorize changing active campaigns.
- Verify claims against actual source/evidence. Distinguish evaluated from supported behavior,
  local tests from VSC acceptance, and submitted jobs from completed validated results.

## VSC execution

- DATA holds the actual Git checkout, specifications and compact logs. Preserve revisions/pins
  used by active or queued jobs. Clone/pull/update submodules here, never in a scratch working copy.
- PROJECT holds persistent assets and project runtimes; prefer versioned immutable containers
  containing the environment. Recreate from recorded specifications at the destination and validate
  before retiring originals. No large-asset fallback to DATA. Check byte/file quotas and backups.
- SCRATCH is disposable job work, never the sole copy of important files. Publish periodically
  and at completion; retire only verified owned workspaces no active/queued/resumable job needs.
  Track failed work for recovery and keep scratch tidy deliberately, not through automatic purge.
- Native GPFS for intensive Mindwell I/O, Lustre for wICE. Direct native PROJECT reads are fine;
  stage only what is necessary. Isolate/lock writable databases and verify publication.
- Optimize time to verified results, not tokens or minimum credits, within the approved budget.
  Submit independent ready jobs together without default `%N` throttles, application pools or
  serialization dependencies. Preserve real preparation/validation/producer-consumer dependencies.
  Automatically refill site submission capacity; never duplicate uncertain submissions.
- Measure resources per task and keep workers × threads inside its allocation. Especially split
  long separable CPU work. Propose targeted throttles only with evidence or an explicit request;
  explain all remaining site versus application limits. See TEMPLATE.md and docs/VSC.md.

## Organization and reporting

- Match experiment folders under `config/`, `notebooks/` and `output/`. Experiment 0 validates
  VSC behavior, optionally split into 0a/0b/...; preserve existing identities when adapting.
- Reusable logic lives in `src/`; experiment launchers/Bash/Slurm in `scripts/`; maintenance in
  `src/utils/`. Paths come from `paths.py`. Non-obvious comments explain why.
- Notebooks contain no `def`/`class`, display figures inline and end with a complete printed
  report in section order. Centralize project colours/sizes in `src/visualize/style.py`.
  Use FigureSaver for PDF-only output, isolated notebook ownership and paper-ready captions.
  Design for final A4 size/readable text; document justified publication-format deviations.
- Keep `docs/CHANGELOG.md` changes as short as possible, newest dates first (`DD-MM-YYYY`).
  Record runs, useful lessons and costly failures in `docs/AGENTS_MEMORY.md` without losing evidence.
- Local shell is PowerShell 5.1: no `&&`, ternary or `??`. Slurm scripts are Linux Bash with LF.

## Verify before delivery

Run `python -m pytest -q` and `python -m ruff check .`; also `python -m src.utils.run_notebooks`
after notebook/visualization edits. No CI or hook runs these automatically. Check changed Bash
syntax. Report actual results and limitations; never imply local tests establish live VSC acceptance.
