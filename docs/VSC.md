# {{PROJECT_NAME}} on VSC

This runbook turns [TEMPLATE.md](TEMPLATE.md#development-and-vsc-validation-loop) into project
commands. Fill the settings below; keep personal logins/allocations in private local configuration.
Shared infrastructure guidance is in the read-only [VSC Library](../vsc-library/README.md).
Check its [review flags](../vsc-library/UPSTREAM_CHANGES.md) and
[live service status](https://status.vscentrum.be/tier2_leuven.html) when diagnosing problems.

## 1. Record project settings

| Setting | Project value |
|---|---|
| Single branch | `main`, or the project's established branch; use the same locally/GitHub/VSC |
| SSH route and verified host key | TODO; actual username stays in private local configuration |
| DATA checkout and frozen revision/pins | TODO; include consumers that prevent updating it |
| Shared PROJECT root per cluster | TODO; native GPFS for Mindwell, Lustre for wICE |
| Container definition/lock, SIF hash, architecture/modules/driver | TODO; tested PROJECT image |
| Cluster, partition, account, QoS | TODO; verify live settings and approved resources |
| Per-task CPUs, memory, GPUs, walltime | TODO; measure requirements and startup/publication margin |
| Validation commands and pass criteria | TODO; experiment0, optionally 0a/0b/... |
| Shards, genuine dependencies and merge checks | TODO; exact coverage and separate writers |
| Submission ceiling/scope and MaxArraySize | TODO; user/account/QoS and broader applicable limits |
| Publication, resume, backup and cleanup checks | TODO; evidence paths and owned workspaces |
| Byte/file quotas and backup/restore destinations | TODO; verify independently for each storage tier |

## 2. Establish SSH access

The user normally runs this in **Windows PowerShell**, completes browser sign-in and approves
KU Leuven Authenticator:

```powershell
step ssh login --context VSC
```

If access is unavailable, diagnose the bounded connection check. For a missing/expired certificate,
tell the user to run that command and **wait for confirmation** before retrying. DNS/timeouts,
host-key errors and failing remote commands need their own diagnosis; renewal does not fix all failures.
Never open authentication flows, bypass MFA or schedule login reminders.

Follow [TEMPLATE.md's Windows setup, expiry check and SSH probe](TEMPLATE.md#vsc-access-windows-and-agents).
The observed certificate lifetime is about 16 hours; inspect its actual validity. Same-account local
agents can share the configured Windows agent; other machines/cloud agents do not inherit it.
Use native Windows `ssh.exe -F none -T`, a bounded LF-delimited stdin script and no trailing remote
command for the observed gateway issue. Preserve host-key checks and inspect stdout, stderr and
expected status markers: empty output with exit 0 is not evidence of successful command execution.

After access is verified, inspect relevant VSC files, logs, quotas and jobs directly. Computational
debugging runs through Slurm within existing permission; access grants no additional experiments,
installs, cancellations, downloads or deletions.

## 3. Edit and test locally, then push

Keep **one branch**, normally `main`; do not create feature/test branches for this workflow.
Edit locally and run everything relevant that can run locally before publishing:

```powershell
python -m pytest -q
python -m ruff check .
```

Also run `python -m src.utils.run_notebooks` after notebook/visualization changes. Review the diff,
commit the tested files and `git push` when authorized. Record the published commit and library pins.
Fix cluster failures locally and repeat this loop rather than patching the remote implementation.

## 4. Pull safely on DATA

Before pulling, confirm the DATA checkout's branch, clean state and lack of active/queued/resumable
consumers of its revision. Wait or use a separate frozen DATA checkout at a recorded commit when
necessary; keep the same single-branch development history. Never update code/runtime still in use.
Send these **remote Bash** commands through the verified SSH stdin channel, replacing placeholders:

```bash
set -eu
cd "$VSC_DATA/{{PROJECT_NAME}}"
BRANCH=main
EXPECTED_COMMIT=COMMIT_SHA
test "$(git branch --show-current)" = "$BRANCH"
test -z "$(git status --porcelain)"
git pull --ff-only
test "$(git rev-parse HEAD)" = "$EXPECTED_COMMIT"
git submodule status
PROJECT_ROOT=/allocated/native/shared/root
RUNTIME="$PROJECT_ROOT/{{PROJECT_NAME}}/runtimes/runtime-v1.sif"
REVISION=$(git rev-parse HEAD)
```

Use the established branch in `BRANCH` if different. Stop on mismatches; do not force-reset, merge
divergent histories or refresh consumer libraries incidentally. Git operations occur on DATA.
The launcher takes explicit paths because Leuven does not inherit arbitrary submission-shell exports.

## 5. Check storage and runtime

- **DATA:** actual Git checkout, dependency specifications and compact logs/manifests/reports.
- **PROJECT:** datasets, weights, checkpoints, retained results, reusable caches and versioned
  **SIF containers containing all project dependencies**. No unpacked venv/Conda trees or persistent
  container sandboxes: file counts are strict. Recreate from recorded definitions/locks for the
  destination; validate architecture, modules/drivers, dependencies and actual CPU/GPU behavior
  before retiring originals. Check bytes and file counts; keep independent backups.
- **SCRATCH, GPFS and Lustre:** temporary isolated job work only. Keep required copies durable;
  aim for no obsolete project workspaces between workloads. Build caches are disposable.

These are project policies, not universal VSC defaults. Use native GPFS for intensive Mindwell I/O,
Lustre for wICE. Read suitable native PROJECT assets directly; copy only necessary cross-mounted
working sets. Verify transfers and isolate/lock writable databases. Never silently fall back to DATA.
Set `VSC_PROJECT_ROOT` or `{{PROJECT_UPPER}}_PROJECT_ROOT` to a shared root; the resolver appends the
project name once. Legacy `*_STAGING_ROOT` aliases remain supported. Record backups separately from
storage lifetime; do not assume PROJECT protection. `myquota` and allocation-specific tools check quotas.

## 6. Validate on VSC and submit independent work

Fill `scripts/slurm/job.slurm` resource/Apptainer-module TODOs first. It requires the DATA checkout,
PROJECT root, PROJECT SIF and expected commit, followed by Python arguments. It rejects unpacked
runtimes, checks code state, creates isolated scratch caches and leaves workspaces for verified cleanup.
Its CPU request uses partition-default memory: check `DefMemPerCPU`, limits and actual allocation.
Do not combine explicit memory with `--cpus-per-task`; see the current Leuven warning in TEMPLATE.md.
An explicit-memory variant must remove that CPU directive and validate the resulting thread budget.

```bash
mkdir -p output/experiment0/logs
sbatch --clusters=wice --array=0-9 scripts/slurm/job.slurm "$PWD" "$PROJECT_ROOT" "$RUNTIME" "$REVISION" -m your_package.validate
```

Replace the module/config and log paths together. `#SBATCH` cannot expand shell variables. The
application must map `SLURM_ARRAY_TASK_ID` to distinct work; an array flag alone repeats a command.
Start bounded, then test extensively against the recorded criteria: container/architecture, native
I/O, numerical correctness, integration, resources, CPU/GPU operations and recovery/publication as
relevant. Local tests or Slurm exit 0 alone do not establish acceptance. Reuse valid successful evidence.

Submit independent work together with no default `%N` throttle or application running-job pool.
Preserve real preparation/validation/producer-consumer dependencies and measured per-task resources.
For work exceeding site submission capacity, prepare ready `sbatch` argument lists in JSON and preview:

```bash
python -m src.utils.submit_jobs config/experiment0/submissions.json --cluster wice --account ACCOUNT --qos QOS --site-submit-limit VERIFIED_LIMIT
```

Add `--submit` when authorized. See TEMPLATE.md for plan format, stable task IDs and array splitting.
Keep this submitter alive: its 60-second capacity polling is separate from the optional 30-minute
progress monitor below. Receipts/locks under `output/manifests/submissions/` survive cleanup. Resume
the same plan to skip accepted work; reconcile uncertain acceptance with Slurm before any retry.

## 7. Inspect progress, including long waits

Use the project's actual cluster/job IDs; keep log reads bounded and inspect required artifacts:

```bash
squeue --clusters=all --me
sacct --clusters=all -j JOB_ID --format=JobID,State,Elapsed,AllocCPUS,TotalCPU,MaxRSS,ExitCode
tail -n 80 output/experiment0/logs/JOB.log
sacctmgr show qos normal,long,debug,interactive format=Name,MaxSubmitJobsPerUser,MaxTRESPerUser
scontrol --clusters=wice show config | grep MaxArraySize
sam-balance
myquota
```

Read logs/stderr, resource use, warnings, coverage and output integrity for every test. Record
revision/image/config, job IDs, outcomes and evidence in manifests and `AGENTS_MEMORY.md`.

For long GPU queues/runs, optionally create **one temporary scheduled check every 30 minutes**
following [the monitoring policy](TEMPLATE.md#long-waits-and-progress-monitoring). Record monitor/job
IDs, cluster, evidence paths and completion criteria. Use a scheduler/host that can access the local
SSH agent; a cloud runner cannot borrow its certificate. Check accounting and outputs before declaring
completion; an empty queue is insufficient. Report meaningful changes, stay quiet when unchanged.
If authentication expires, request manual renewal and wait/pause rather than opening MFA or spamming.
After assessing/reporting all terminal outcomes, **delete the monitor automatically**, retaining its
final record and unresolved cleanup/failures. Remove it also if abandoned/cancelled. Monitoring does
not authorize retries, submissions, cancellations or remote deletion.

## 8. Publish, clean up and report

Publish required results/checkpoints to PROJECT periodically and at completion; verify content and
write completion pointers last. Test checkpoint/signal/requeue behavior before enabling it; the
launcher provides no automatic checkpoint or requeue protocol. Scratch loss must not erase required work.

Track every temporary checkout/script/transfer/test artifact/workspace created on all tiers.
After verified publication and confirmation that no active/queued/resumable job needs it, delete
only the exact obsolete owned path. Review both GPFS and Lustre project scratch; preserve recovery
state. Never wipe shared roots or rely on purge/touching. Node-local scratch can vanish at job end.
Record cleanup done/deferred and why; preserve required DATA evidence, PROJECT assets/images and backups.

```bash
python -m src.utils.clean_run                     # preview disposable output
python -m src.utils.clean_run --clean             # preserve results, receipts and workspaces
python -m src.utils.clean_run --clean --processed # explicitly rebuild processed inputs
```

Stop writers and retain useful logs first. These commands do not retire scratch workspaces or delete
raw inputs, checkpoints, runtimes, reusable caches or libraries. Report local checks and actual VSC
acceptance separately, including remaining failures, deferred cleanup and monitor removal.
