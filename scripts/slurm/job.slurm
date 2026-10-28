#!/bin/bash -l
# Copy/adapt per experiment. Submit from DATA; all resource TODOs need measured values.
# Arguments: DATA_CHECKOUT SHARED_PROJECT_ROOT PROJECT_RUNTIME EXPECTED_COMMIT PYTHON_ARGS...
# Runtime: a versioned .sif (preferred) or an absolute project-environment Python executable.
# Arrays: --array=0-9 by default, no % throttle; application selects SLURM_ARRAY_TASK_ID.
#SBATCH --job-name={{PACKAGE_NAME}}
#SBATCH --account=TODO_credit_account
#SBATCH --clusters=TODO_cluster
#SBATCH --partition=TODO_partition
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=TODO_cpus_per_task
#SBATCH --mem=TODO_host_memory
#SBATCH --time=TODO_walltime
##SBATCH --gpus-per-node=1
# Create these directories before submission; Slurm opens logs before Bash runs.
#SBATCH --output=output/experiment0/logs/%x_%A_%a.log
#SBATCH --error=output/experiment0/logs/%x_%A_%a_error.log
#SBATCH --open-mode=append
set -euo pipefail

[[ $# -ge 5 ]] || { echo "See docs/VSC.md for checkout, PROJECT, runtime, commit and Python arguments." >&2; exit 2; }
for path in "$1" "$2" "$3"; do
    [[ "$path" = /* ]] || { echo "Paths must be absolute: $path" >&2; exit 2; }
done
REPO=$(realpath "$1")
export VSC_PROJECT_ROOT=$(realpath "$2")
export "{{PROJECT_UPPER}}_PROJECT_ROOT=$VSC_PROJECT_ROOT"
RUNTIME=$(realpath "$3")
EXPECTED_COMMIT=$4
shift 4
ASSETS="$VSC_PROJECT_ROOT/{{PROJECT_NAME}}"
DATA=$(realpath "${VSC_DATA:?}")
[[ "$REPO/" == "$DATA/"* ]] || { echo "Checkout must be on DATA." >&2; exit 2; }
for protected in "$DATA" "${VSC_HOME:-}" "${VSC_SCRATCH:-}" "${VSC_SCRATCH_NODE:-}" \
                 "${VSC_SCRATCH_GPFS1:-}" "${VSC_SCRATCH_LUSTRE1:-}"; do
    [[ -n "$protected" ]] || continue
    protected=$(realpath "$protected")
    if [[ "$VSC_PROJECT_ROOT/" == "$protected/"* || "$protected/" == "$VSC_PROJECT_ROOT/"* ]]; then
        echo "PROJECT must be separate from DATA/HOME/SCRATCH." >&2; exit 2
    fi
done
[[ "$RUNTIME/" == "$ASSETS/runtimes/"* ]] || { echo "Runtime must be under PROJECT/<project>/runtimes/." >&2; exit 2; }
[[ -d "$ASSETS" ]] || { echo "Missing PROJECT assets; no fallback to DATA." >&2; exit 2; }
cd "$REPO"
# Refuse a checkout changed while the job waited; keep this revision frozen throughout execution.
[[ "$(git rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || { echo "Checkout revision changed." >&2; exit 2; }
git diff --quiet HEAD || { echo "Tracked files or submodule pins changed." >&2; exit 2; }

module load TODO_runtime_module  # compatible Apptainer or Python module for the target nodes
REPORTS="$DATA/{{PROJECT_NAME}}/output"
mkdir -p "$REPORTS"
WORK_ROOT="${VSC_SCRATCH_NODE:-${VSC_SCRATCH:?}}/{{PROJECT_NAME}}"
mkdir -p "$WORK_ROOT"
WORK=$(mktemp -d "$WORK_ROOT/${SLURM_JOB_ID:?}_${SLURM_ARRAY_TASK_ID:-single}_XXXXXX")
export TMPDIR="$WORK/tmp" XDG_CACHE_HOME="$WORK/cache" HF_HOME="$WORK/cache/huggingface"
export APPTAINER_CACHEDIR="$WORK/apptainer-cache" APPTAINER_TMPDIR="$WORK/tmp"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:?}" MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK" BLIS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMEXPR_NUM_THREADS="$SLURM_CPUS_PER_TASK" OMP_MAX_ACTIVE_LEVELS=1

if [[ "$RUNTIME" == *.sif ]]; then
    [[ -f "$RUNTIME" ]] || { echo "Missing image: $RUNTIME" >&2; exit 2; }
    # Carry only explicit paths, resource identity and thread settings into the immutable image.
    for name in "{{PROJECT_UPPER}}_PROJECT_ROOT" VSC_DATA VSC_PROJECT_ROOT VSC_SCRATCH VSC_SCRATCH_NODE TMPDIR XDG_CACHE_HOME HF_HOME \
                OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS BLIS_NUM_THREADS NUMEXPR_NUM_THREADS \
                OMP_MAX_ACTIVE_LEVELS CUDA_VISIBLE_DEVICES ${!SLURM_@}; do
        if [[ -v "$name" ]]; then export "APPTAINERENV_$name=${!name}"; fi
    done
    runner=(apptainer exec --cleanenv --bind "$REPO:$REPO:ro" --bind "$REPORTS:$REPORTS:rw"
            --bind "$ASSETS:$ASSETS" --bind "$WORK_ROOT:$WORK_ROOT")
    if [[ -n "${SLURM_JOB_GPUS:-}" || -n "${CUDA_VISIBLE_DEVICES:-}" ]]; then runner+=(--nv); fi
    runner+=("$RUNTIME" python)
else
    [[ -x "$RUNTIME" ]] || { echo "Missing environment interpreter: $RUNTIME" >&2; exit 2; }
    runner=("$RUNTIME")
fi
"${runner[@]}" -c 'from src.utils.paths import describe; print(describe())'
echo "commit=$EXPECTED_COMMIT runtime=$RUNTIME workspace=$WORK"
# The application publishes periodically and on completion. A shell trap cannot prove safe cleanup.
set +e
srun "${runner[@]}" "$@"
status=$?
echo "exit=$status; verify publication and all active/queued/resumable users before removing $WORK"
exit "$status"
