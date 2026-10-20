# Changelog

## 20-10-2026

- Hardened cleanup against linked paths, added atomic report writes and explicit cluster allocation configuration, and fixed retained notebook summaries and failed-rerun reporting.
- Removed stale setup/configuration claims and README duplication; kept configuration, provenance schemas and verification commands project-defined.
- Fixed initializer escaping and preflight checks; aligned editor protection, library commands and Slurm guidance with the independent-library layout.

- Made VSC the only default library; removed the TFM registration, documented optional independent libraries and canonical propagation, and generalized the pin helper and initializer.

- Added the independent read-only VSC Library submodule and daily pin-update proposals; shared HPC guidance moved out of TFM Library, with project instructions retained in docs/VSC.md. No cluster workload was submitted.

What changed in this repository. **One chapter per date, `DD-MM-YYYY`, newest at the
top.** Terse: what changed, and why if it is not obvious. All rules and rule changes are
recorded here.

Edits to the repository. The runs and the dead ends go in
[`AGENTS_MEMORY.md`](AGENTS_MEMORY.md) — keep them separate, mixing them makes both unreadable.

Conventions:

- **As short as possible.** What changed, plus the *why* only when it is not obvious from the
  *what* — after an em dash. Most changes fit on one line; a genuinely large one can take more, but
  it should still be the shortest version that is complete. The detail belongs in the commit, and a
  changelog nobody skims is a changelog nobody reads.
- **Newest date first.** A reader wants the current state, not the archaeology.
- Dates are `DD-MM-YYYY`. Not ISO, not `Jan 5`. One format, sortable by eye.
- Group a date's bullets under `### Added` / `### Changed` / `### Removed` / `### Fixed` only once
  there are enough to need it.

---

## New-project starting point

- Record the new project's creation date and origin:
  [andreasgoethals/0.-Template](https://github.com/andreasgoethals/0.-Template).
- `vsc-library/` is included as a read-only submodule; TFM and DM are optional. Record the pin here whenever it moves,
  because a result depends on the literature it was checked against.
