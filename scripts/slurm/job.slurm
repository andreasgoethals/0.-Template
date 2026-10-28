#!/bin/bash -l
# ---------------------------------------------------------------------------
# {{PROJECT_NAME}} — SLURM job template.
#
# Copy this per experiment; do not parameterise one script into unreadability.
#   mkdir -p output/logs
#   sbatch --clusters=wice scripts/slurm/job.slurm python -m <your_project_entrypoint>
#
# THIS IS BASH ON LINUX, not PowerShell. `&&` is fine here.
#
# Fill in the TODOs from docs/VSC.md before submitting; no resource size suits every project.
# Use arrays for independent CPU shards; the entrypoint must select SLURM_ARRAY_TASK_ID.
# For arrays, override log paths with %A_%a to make shard identity explicit.
# ---------------------------------------------------------------------------
#SBATCH --job-name={{PACKAGE_NAME}}
#SBATCH --account=TODO_credit_account
#SBATCH --clusters=TODO_cluster
#SBATCH --partition=TODO_partition
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=TODO_cpus_per_task
#SBATCH --mem=TODO_host_memory
#SBATCH --time=TODO_walltime
# Uncomment for a GPU partition:
##SBATCH --gpus-per-node=1

# Submit from the repository root and create output/logs BEFORE sbatch opens these files.
#SBATCH --output=output/logs/%x_%j.log
#SBATCH --error=output/logs/%x_%j_error.log
#SBATCH --open-mode=append

set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "Supply this project's compute command after job.slurm; see docs/VSC.md." >&2
    exit 2
fi

PROJECT="{{PROJECT_NAME}}"
REPO="$VSC_DATA/$PROJECT"

module load TODO_python_module          # select a compatible Python 3.11/3.12 module
source "$REPO/.venv/bin/activate"
cd "$REPO"

# TODO set the allocated {{PROJECT_UPPER}}_STAGING_ROOT here (or source a project environment
# file). Leuven does not inherit arbitrary exports from the submission terminal.
# TODO bound process workers AND their BLAS/OpenMP threads to SLURM_CPUS_PER_TASK;
# multiple full-core thread pools oversubscribe CPUs and make parallel jobs slower.

# Record where this run will write, before it writes anything. A run whose output cannot be
# found six months later is a run that did not happen.
python -c "from src.utils.paths import describe; [print(f'{k:>16}: {v}') for k, v in describe().items()]"

# Automatic checkpoint/requeue is deliberately not implemented: the application must
# confirm a complete checkpoint before a requeue. B:USR1 signals only the batch shell,
# not the training process. See docs/VSC.md before adding a project-specific protocol.
srun "$@"
