# Agents' memory — runs and dead ends

## 20-10-2026

- **Tried:** reviewed the inherited `B:USR1`, 30-second sleep and automatic requeue example.
  **Result:** code review found no signal forwarding or checkpoint confirmation; no cluster job was run.
  **Why:** `B:` signals only the batch shell; a delay is not a checkpoint acknowledgement.
  **Instead:** use the explicit-command launcher; add requeue only with a tested application protocol.

- Library maintenance now runs from the canonical `0. Literature` workspace. The template consumes only VSC; TFM and DM are optional. Consumer copies remain read-only.

- Added the independent read-only VSC Library submodule and daily pin-update proposals; shared HPC guidance moved out of TFM Library, with project instructions retained in docs/VSC.md. No cluster workload was submitted.

What is worth carrying between sessions: **the cluster runs that have been done**, and **the things
that turned out not to work**. Read it before starting; add to it as you go.

Not the changelog — that records edits to the repository. This records experience: what was run,
what came out, and what is already known to fail.

**Keep it short.** One line per run, four per dead end. Newest first, dates `DD-MM-YYYY`. Never
delete an entry: a run you would otherwise repeat and a dead end you already paid for are both
evidence.

## Runs

One row per cluster run worth remembering — which is most of them, because *"have we already tried
that configuration?"* is the question this table exists to answer.

| Date | Run | Outcome | Notes |
|---|---|---|---|
| | | | |

- **Run** — the config or arm, and the commit if it matters.
- **Outcome** — `done` / `walltime` / `OOM` / `crashed` / `diverged` / `cancelled`.
- **Notes** — one line: the headline number, the output path if it is worth finding again, or the
  single thing the run showed. A number here saves re-reading `output/results/`.

## Dead ends

Anything that cost more than a couple of minutes and did not work — including what you eventually
fixed, because the fix is one changelog line and the dead end was the hour.

```
### <short name for the attempt>
- **Tried:** what was done.
- **Result:** what happened — the error, the wrong number, the silent no-op.
- **Why:** the underlying reason, once understood.
- **Instead:** what to do, and the cheap check that would have caught it sooner.
```

_Nothing yet._
