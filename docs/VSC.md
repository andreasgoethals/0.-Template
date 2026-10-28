# {{PROJECT_NAME}} on the KU Leuven VSC

Shared infrastructure reference: [VSC Library](../vsc-library/README.md). The parent Git commit pins its revision; inspect it with `git submodule status -- vsc-library`.
Its [official repository snapshot](<../vsc-library/VSC Repository.txt>),
[guides](../vsc-library/guides/) and [Slurm templates](<../vsc-library/slurm templates/README.md>)
are read-only. Keep this project's actual paths, environment, resource choices,
submission/resume steps and run evidence in this file or the project's own run logs.
Check [upstream review flags](../vsc-library/UPSTREAM_CHANGES.md) and the
[live Leuven status](https://status.vscentrum.be/tier2_leuven.html) before applying a changed policy.

How to run this project on the cluster. The authoritative cluster documentation is in the
`vsc-library/` submodule — read it there and keep this file as *this project's* answer to it, not a
copy. Fill in the `TODO`s before the first submission.

## Speed-first execution

Follow [the speed-first policy in TEMPLATE.md](TEMPLATE.md#speed-first-execution-open-ondemand-and-slurm):
minimize end-to-end turnaround, not tokens/credits, within the approved budget. Especially
split long independent CPU tests/evaluations into balanced shards and submit them together.
Open OnDemand apps use scheduled resources; an editor session is not the campaign runner.
Use its login shell or SSH for batch submission, never for heavy computation. Leuven's
Desktop app does not expose Slurm commands; use the login-shell feature instead.

Record this project's measured choices here rather than inheriting arbitrary limits:

| Decision | Project value |
|---|---|
| Independent work / shard map / merge check | TODO; preserve exact coverage and seeds |
| Cluster, CPU partition and compatible environment | TODO |
| Per-shard CPUs, peak RAM and walltime including setup margin | TODO; measure a representative shard |
| Array size and maximum useful concurrency | TODO; current QoS/account limits and I/O capacity |
| Observed queue + setup + execution + merge time | TODO; compare with serial execution |
| Shared setup, output ownership and any unavoidable serial stage | TODO |

For ten independent shards, `--array=0-9%10` permits up to ten concurrent tasks. The entrypoint
must read `SLURM_ARRAY_TASK_ID`; applying this flag to an unsharded command merely repeats it.
Use distinct `.log` paths such as `output/logs/%x_%A_%a.log`, and separate shard outputs.
Use same-cluster `afterok` dependencies for preparation/merge; do not assume cross-cluster
dependencies work. Query limits and inspect pending reasons with the commands in TEMPLATE.md.
Do not choose a low concurrency cap merely to save credits, or a huge cap that slows shared I/O.

**Log every run** in the Runs table of [`AGENTS_MEMORY.md`](AGENTS_MEMORY.md): one row with the
config, the outcome and the headline number. That table is what stops a configuration being
resubmitted months after it already failed.

## The machines

| Host | Role |
|---|---|
| **wICE login service** | Shared login nodes — editing, submission and small setup only. |
| **wICE** | general-purpose compute partitions |
| **Mindwell** | CPU, GPU, large-memory and interactive compute partitions |

```bash
ssh vsc<number>@login.hpc.kuleuven.be
```

Do not rely on outbound internet from compute nodes; stage required assets before execution.
Use approved transfer/setup routes: only lightweight operations on login nodes, substantial
builds or transfers in suitable allocations. Follow the library's software/storage guides.

## Storage — two tiers, one resolver

On **both** tiers everything lives inside a folder named after the project. Never build these
paths by hand: `src/utils/paths.py` is the only module that constructs them, and it collapses both
tiers to the repository root off-cluster, so the same code runs on a laptop unconfigured.

| tier | path | holds | quota |
|---|---|---|---|
| **project storage** | `<configured staging root>/{{PROJECT_NAME}}/` | datasets, checkpoints, caches, **`output/results/`** | allocation-specific |
| **personal data** | `$VSC_DATA/{{PROJECT_NAME}}/` | the repository, and the rest of `output/` | 75 GiB |
| scratch | `$VSC_SCRATCH/` | working scratch only | **purged after 30 days** |

- **Personal DATA is backed up; confirm the actual group-project storage protection policy.** They differ in size and in convenience: you can browse `$VSC_DATA`
  directly, while anything on project storage has to be pulled down locally first (PowerShell,
  `scp`/`rsync`) before you can look at it. So the big, rarely-read things go to project storage and
  everything you actually want to open stays on `$VSC_DATA`.
- `$VSC_DATA` is 75 GiB. One forgotten checkpoint directory fills it, and then every job that
  writes a log fails too.
- Project storage has a **low inode budget** — few big files, not a hundred thousand small ones.
  Per-step records therefore go to `$VSC_DATA`.
- Scratch's purge is on **access** time, and `mv` and timestamp-preserving `rsync` do **not** count
  as an access, so freshly staged data can vanish almost immediately. Copy, then
  verify the scratch copy using the current storage guide.
- Use native **Lustre on wICE** and **GPFS on Mindwell** for intensive I/O; stage between them
  before compute. P100/V100 nodes cannot access GPFS.

Configure the allocated big-file tier before cluster use. No allocation is guessed.
The project name is appended; supply the shared root, not the project directory.
The same override supports an external drive locally:

```bash
export {{PROJECT_UPPER}}_STAGING_ROOT=/some/other/place
```

Set it inside the job script (or a project environment file sourced there), not just in the
submission terminal: Leuven does not propagate arbitrary submission-shell variables by default.
If using `--export`, preserve the site's minimal environment as documented in
[Leuven Slurm](https://docs.vscentrum.be/leuven/slurm_specifics.html#environment-propagation).

## Environment

```bash
module load TODO_python_module             # select a compatible Python 3.11/3.12 module
python -m venv $VSC_DATA/{{PROJECT_NAME}}/.venv
source $VSC_DATA/{{PROJECT_NAME}}/.venv/bin/activate
pip install -e ".[dev]"
```

The venv lives on `$VSC_DATA`: it must survive the scratch purge and be backed up, and it is small.

## Submitting

```bash
mkdir -p output/logs
sbatch --clusters=wice scripts/slurm/job.slurm python -m <your_project_entrypoint>
squeue --clusters=all --me
sacct --clusters=all -j <jobid> --format=JobID,JobName,State,Elapsed,AllocCPUS,TotalCPU,MaxRSS,ExitCode
scancel --clusters=wice <jobid>
```

| Knob | Where | TODO |
|---|---|---|
| cluster | `--clusters` | `wice` or `mindwell`; use it explicitly for submission/cancellation |
| partition | `#SBATCH --partition` | which partition this project uses |
| CPU / RAM | `--cpus-per-task`, `--mem` | measured per-shard need, accounting for worker threads |
| walltime | `#SBATCH --time` | realistic shard duration plus margin, within the partition limit |
| array | `--array` | balanced shard IDs and useful concurrency, not sequential launches |
| credits | `#SBATCH --account` | the credit account to charge |
| GPUs | `#SBATCH --gpus-per-node` | what this project actually needs |

When the job comes back, add its row to the Runs table in
[`AGENTS_MEMORY.md`](AGENTS_MEMORY.md) — `done` / `walltime` / `OOM` / `crashed` / `diverged`, plus
one line of notes.

## Outliving the walltime

Any run that can exceed the limit must be **resumable** — a job killed at the walltime is
otherwise a total loss.

1. Checkpoint on a fixed interval to project storage, plus a small `state.json` on `$VSC_DATA`
   naming the latest complete one. Write the pointer **last**, so a job killed mid-write points at
   the previous complete checkpoint rather than a truncated one.
2. On start, read the pointer and resume. A fresh run and a resumed run take the **same code
   path** — a resume path only exercised after a crash is a resume path that does not work.
3. Add requeue handling only after implementing and testing the application's checkpoint
   protocol. `#SBATCH --signal=B:USR1@300` signals only the batch shell, not the application;
   forwarding the request and confirming a complete checkpoint are the project's responsibility.
   A fixed sleep is not confirmation. Requeue only after a successful checkpoint, with bounded
   retries and a verified resume path. See the [Slurm signal documentation](https://slurm.schedmd.com/sbatch.html#OPT_signal).
4. Make each step idempotent: a completed result is reused or replaced atomically, so a retry
   never doubles a result file. Protect artifacts that cost a training run or paid call.

The supplied job script does not automatically checkpoint or requeue. It runs the explicit
compute command supplied after the script name and preserves its exit status.

## Getting results back, and cleaning up

Reports, logs and results are under `output/`; caches and checkpoints have separate roots.

```bash
rsync -av vsc<number>@login.hpc.kuleuven.be:$VSC_DATA/{{PROJECT_NAME}}/output/ ./output/
```

`output/results/` is on project storage, so it is a second copy from
`<configured staging root>/{{PROJECT_NAME}}/output/results/`.

```bash
python -m src.utils.clean_run                       # list what the previous run left
python -m src.utils.clean_run --clean               # wipe output/ on both tiers
python -m src.utils.clean_run --clean --processed    # ...and the data/processed cache
```

The default cleanup targets generated `output/` on both tiers. `--processed` additionally
targets `data/processed/`; raw data, checkpoints and library submodules are outside those
targets. Stop writers before cleaning, preview before applying, and keep irreplaceable artifacts
outside cleanup targets.
