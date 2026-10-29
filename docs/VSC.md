# {{PROJECT_NAME}} on VSC

Project policy: [access](TEMPLATE.md#vsc-access-windows-and-agents),
[storage](TEMPLATE.md#vsc-storage-policy), [execution](TEMPLATE.md#speed-first-execution-open-ondemand-and-slurm).
Infrastructure reference:
[VSC Library](../vsc-library/README.md), read-only at the parent's gitlink. Check its
[review flags](../vsc-library/UPSTREAM_CHANGES.md) and [live status](https://status.vscentrum.be/tier2_leuven.html).
Fill these project choices before submission; this file is a runbook, not a second VSC manual.

## Project settings

| Setting | Project value |
|---|---|
| SSH route and verified host key | TODO; private local username/config, public-safe placeholders here |
| DATA checkout, frozen revision and submodule pins | TODO; actual Git checkout including `.git` |
| Shared PROJECT root per cluster | TODO; GPFS for intensive Mindwell I/O, Lustre for wICE |
| Container definition/lock, SIF hash and validated architecture/modules | TODO; versioned PROJECT image |
| Cluster, partition, account, QoS | TODO; query live site settings |
| CPUs, host RAM, GPUs and walltime per task | TODO; measured requirement + startup/publication margin |
| Independent shard map and genuine dependencies | TODO; exact coverage, unique outputs, validated merge |
| Site pending+running ceiling and its scope; MaxArraySize | TODO; include applicable association/partition limits |
| Validation stages, pass criteria and evidence paths | TODO; experiment0, optionally 0a/0b/... |
| Publication/resume and scratch retirement checks | TODO; periodic publication, final verification, job ownership |
| Byte/file quotas, backup destinations and restore procedure | TODO; independent backups of irreplaceable outputs |

## Access and runtime

Follow TEMPLATE.md's one-time Windows setup and manual `step ssh login --context VSC` renewal;
check actual expiry. Agents use its bounded stdin-script probe, then inspect relevant files/logs,
results, quotas and jobs directly. Use Slurm for computational debugging within existing permission.
No automatic login/reminders, pasted-output routine or implied permission for destructive actions.

Clone/pull/update submodules **on DATA**; preserve code/pins/runtimes used by active or queued jobs.
Build dependencies into a versioned **PROJECT SIF container**, from a definition/lock in Git,
on an authorized setup allocation. No unpacked PROJECT venv/Conda trees: file counts are strict.
Recreate for the destination; validate architecture, modules/drivers, dependencies and actual
workloads before retiring originals. Check byte/file quotas (`myquota`, allocation-specific tools)
and independent backups. Temporary builds/caches use SCRATCH; completed images remain on PROJECT.

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

## Deploy a locally tested revision

Follow [the development loop](TEMPLATE.md#development-and-vsc-validation-loop). After local tests,
review/commit/push; use the documented SSH stdin route for these remote Bash commands. First verify
that the DATA checkout is clean, on the intended branch and unused by active/queued/resumable jobs;
otherwise create a separate DATA checkout. Replace the commit placeholder with the published SHA:

```bash
set -eu
cd "$VSC_DATA/{{PROJECT_NAME}}"
git status --short --branch
git pull --ff-only
EXPECTED_COMMIT=COMMIT_SHA
test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT"
git submodule status
```

Then run this project's required cluster tests via Slurm using the recorded PROJECT container.
Fill in test commands/coverage and pass criteria above; inspect logs, resource use and output
integrity before accepting results. Fix locally and redeploy. Track created temporary paths and
record their cleanup or justified deferral after the publication/ownership checks below.

## Submit independent work

Fill `scripts/slurm/job.slurm` resource/Apptainer-module TODOs first. It requires a PROJECT SIF,
then Python arguments; unpacked runtimes are rejected. GPU images need a compatible host
driver and real GPU validation. The example starts with experiment-0 log paths; change them and
the application config together when copying it. `#SBATCH` directives cannot expand `$variables`.
It requests CPUs and partition-default memory: check `DefMemPerCPU`, limits and actual allocation.
Do not add explicit memory alongside `--cpus-per-task`; see TEMPLATE.md's current Leuven warning.
If explicit memory is necessary, remove the CPU directive and adapt/validate the thread budget.

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

Keep the submitter alive. It fills verified pending+running capacity and polls every 60 seconds
when full/unavailable; check broader association/partition limits too. No running-job cap is added.
Explicitly throttled arrays wait for whole-array admission; see TEMPLATE.md for splitting/recovery rules.

Receipts/locks live in `output/manifests/submissions/` and survive cleanup. Resume the same plan
to skip accepted IDs. Never delete a receipt or clear an uncertain `in_flight` entry blindly:
reconcile with `squeue`/`sacct` and record the accepted ID, or establish definite nonacceptance.
Remove a stale lock only after its owner stopped. Review changed plans to avoid duplicate work.
Generic QoS errors stop for diagnosis; failed queries never mean an empty queue.

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
then remove only that owned path. Check **both GPFS and Lustre project scratch** for obsolete
workspaces; aim for empty between workloads only when nothing needs recovery or queued/active use.
Never wipe shared roots or rely on automatic purge/touching. Node-local scratch is even less
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
