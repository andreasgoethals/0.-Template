# Changelog

## 28-10-2026

- Establish DATA/PROJECT/SCRATCH policy, PROJECT runtimes and protected retained results; remove fallback storage and arbitrary concurrency defaults, add resumable site-capacity submission, and compact the docs.
- Add flexible experiment-first organization and staged VSC validation; support nested notebooks, isolated outputs and matching examples.
- Make VSC turnaround speed the priority: shard independent CPU work, submit ready jobs together, and document OnDemand/Slurm limits and safe parallel execution.
- Make all three library registration/update paths explicit; align the launcher and VSC setup with current site guidance.

## 20-10-2026

- Standardized the optional DM Library mountpoint as `dm-library` in helpers, initializer exclusions, editor settings and documentation.

- Hardened cleanup against linked paths, added atomic report writes and explicit cluster allocation configuration, and fixed retained notebook summaries and failed-rerun reporting.
- Removed stale setup/configuration claims and README duplication; kept configuration, provenance schemas and verification commands project-defined.
- Fixed initializer escaping and preflight checks; aligned editor protection, library commands and Slurm guidance with the independent-library layout.

- Made VSC the only default library; removed the TFM registration, documented optional independent libraries and canonical propagation, and generalized the pin helper and initializer.

- Added the independent read-only VSC Library submodule and daily pin-update proposals; shared HPC guidance moved out of TFM Library, with project instructions retained in docs/VSC.md. No cluster workload was submitted.

## New projects

Start a project changelog with its creation date and template origin. Record substantive
changes and library-pin updates briefly, newest dates first (`DD-MM-YYYY`).
