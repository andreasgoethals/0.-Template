# {{PROJECT_NAME}} on VSC

Project policy: [TEMPLATE.md](TEMPLATE.md#vsc-storage-policy). Infrastructure reference:
[VSC Library](../vsc-library/README.md), read-only at the parent's gitlink. Check its
[review flags](../vsc-library/UPSTREAM_CHANGES.md) and [live status](https://status.vscentrum.be/tier2_leuven.html).
Fill these project choices before submission; this file is a runbook, not a second VSC manual.

## Project settings

| Setting | Project value |
|---|---|
| DATA checkout, frozen revision and submodule pins | TODO; actual Git checkout including `.git` |
| Shared PROJECT root per cluster | TODO; GPFS for intensive Mindwell I/O, Lustre for wICE |
| Runtime specification, image hash / environment version | TODO; versioned PROJECT runtime |
| Cluster, partition, account, QoS | TODO; query live site settings |
| CPUs, host RAM, GPUs and walltime per task | TODO; measured requirement + startup/publication margin |
| Independent shard map and genuine dependencies | TODO; exact coverage, unique outputs, validated merge |
| Site pending+running ceiling and its scope; MaxArraySize | TODO; include applicable association/partition limits |
| Validation stages, pass criteria and evidence paths | TODO; experiment0, optionally 0a/0b/... |
| Publication/resume and scratch retirement checks | TODO; periodic publication, final verification, job ownership |
| Byte/file quotas, backup destinations and restore procedure | TODO; independent backups of irreplaceable outputs |

## Checkout, assets and runtime

Clone/pull/update submodules **on DATA**. Preserve the revision and runtime of active or queued
jobs; use a separate DATA checkout for changed code. Environment specifications belong in Git;
installed environments and images belong on PROJECT. Never move a populated venv: recreate at
its final destination, validate actual workloads and only then retire an unused original.

Prefer an immutable Apptainer SIF containing the environment; build from a recorded definition
and dependency specification on an allowed setup allocation. A versioned PROJECT venv/Conda
environment is an alternative. Containers reduce small-file pressure; neither their compatibility
nor their quota use is automatic. Check bytes and file counts (`myquota`, allocation-specific
tools). Do not assume PROJECT has independent backups. Keep build caches temporary on SCRATCH.

On the login shell, choose actual paths (examples are placeholders):

```bash
cd "$VSC_DATA/{{PROJECT_NAME}}"
PROJECT_ROOT=/allocated/native/shared/root
RUNTIME="$PROJECT_ROOT/{{PROJECT_NAME}}/runtimes/runtime-v1.sif"
REVISION=$(git rev-parse HEAD)
```

The launcher receives these explicitly because Leuven does not propagate arbitrary exports.
It sets `VSC_PROJECT_ROOT`; Python also accepts `{{PROJECT_UPPER}}_PROJECT_ROOT` and the legacy
`*_STAGING_ROOT` aliases. Roots are shared; the resolver adds `{{PROJECT_NAME}}` exactly once.
Do not leave a conflicting higher-priority override in the job environment.

Native PROJECT assets may be read directly. Stage only needed cross-filesystem working sets;
verify copies and database locking before compute. Preserve original inputs and checkpoints.
No cluster downloads, environment installs or migrations are authorized just by this template.

## Submit independent work

Fill `scripts/slurm/job.slurm` resource/module TODOs first. It expects a PROJECT SIF or absolute
PROJECT environment interpreter, then Python arguments. GPU images need a compatible host
driver and real GPU validation. The example starts with experiment-0 log paths; change them and
the application config together when copying it. `#SBATCH` directives cannot expand `$variables`.

```bash
mkdir -p output/experiment0/logs
sbatch --clusters=wice --array=0-9 scripts/slurm/job.slurm "$PWD" "$PROJECT_ROOT" "$RUNTIME" "$REVISION" -m your_package.validate
```

The application must map `SLURM_ARRAY_TASK_ID` to unique work; the flag alone only repeats a
command. **No `%N` throttle by default.** Slurm schedules all eligible work. Optional throttles
require a user request or a proposed limit supported by measured storage/service/correctness
evidence. Request appropriate resources per task; retain only genuine dependencies/gates.

For more work than fits the site's submission ceiling, prepare a JSON list of **ready** `sbatch`
argument lists, e.g. `config/experiment0/submissions.json`. An entry can represent one job or an
array with task IDs below the verified MaxArraySize. Unthrottled arrays split automatically into
available submission slots with original IDs preserved. Declare arrays in the plan; select work
from stable IDs, not per-chunk array counts/min/max. Example shape (replace paths, revision,
module and work selection):

```json
[
  ["--array=0-9", "scripts/slurm/job.slurm", "/DATA/Project", "/PROJECT", "/PROJECT/Project/runtimes/runtime.sif", "COMMIT_SHA", "-m", "your_package.validate"]
]
```

Preview, then run the same command with `--submit` after authorization:

```bash
python -m src.utils.submit_jobs config/experiment0/submissions.json --cluster wice --account ACCOUNT --qos QOS --site-submit-limit VERIFIED_LIMIT
```

Use a persistent submitter session. It fills available **pending+running** capacity, polls at
60-second intervals when full/unavailable and refills automatically. The ceiling must match
the selected user/account/QoS/cluster scope; verify broader limits too. Sequential submission
RPCs preserve reliable receipts, not sequential job execution. Array `%N` is passed through
only if deliberately present in the plan; such arrays wait for whole-array admission to preserve
the requested throttle. Split oversized throttled arrays only after review. The helper adds no
dependency or resource inflation.

Receipts/locks live in `output/manifests/submissions/` and survive cleanup. Resume the same plan
to skip accepted IDs. Never delete a receipt or clear an uncertain `in_flight` entry blindly:
reconcile with `squeue`/`sacct` and record the accepted ID, or establish definite nonacceptance.
Remove a stale submitter lock only after confirming its owner stopped. Changed plans need review;
do not resubmit already accepted work under a new receipt. Generic QoS errors may mean invalid
resources, not capacity, and stop for diagnosis. Failed queries never mean an empty queue.

## Verify, publish and retire

```bash
squeue --clusters=all --me
sacctmgr show qos normal,long,debug,interactive format=Name,MaxSubmitJobsPerUser,MaxTRESPerUser
scontrol --clusters=wice show config | grep MaxArraySize
sacct --clusters=all -j JOB_ID --format=JobID,State,Elapsed,AllocCPUS,TotalCPU,MaxRSS,ExitCode
sam-balance
myquota
```

Record queue/setup/compute/merge time, CPU/RAM/I/O use, source/runtime/config identities and
validated outputs. Experiment 0 checks relevant behavior on VSC; local tests and exit codes
alone are insufficient. Log every run/outcome in `AGENTS_MEMORY.md`.

Publish required results and checkpoints to PROJECT periodically and on completion, verify them,
then update completion pointers. Resume only compatible complete state. Test signal forwarding,
checkpoint acknowledgement and any requeue protocol before enabling it; the launcher supplies none.
Required results must survive a killed job, failed node and scratch loss.

The launcher prints its unique scratch workspace and does not delete it. After publication,
verify all expected files and confirm no active, queued or resumable job needs that workspace;
then remove only that owned path. Track incomplete/recoverable work and regularly retire finished
workspaces. Never rely on automatic purge or periodic touching. Node-local scratch is even less
durable: the site may remove it at job end. Keep independent backups of irreplaceable results.

For local analysis, merge the DATA and PROJECT output trees by their relative paths without
overwriting protected results. SCP/SFTP/rsync paths must be explicit; local PowerShell does not
expand remote `$VSC_DATA`. Use approved transfer allocations for substantial copies.

```bash
python -m src.utils.clean_run                     # preview disposable output across experiments
python -m src.utils.clean_run --clean             # preserve results, receipts and workspaces
python -m src.utils.clean_run --clean --processed # additionally rebuild processed inputs
```

Stop writers and retain useful logs first. Raw inputs, weights, runtimes, reusable caches and
libraries stay protected. Scratch retirement always requires its separate checks above.
