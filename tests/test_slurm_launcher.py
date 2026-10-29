"""Exercise container-only launch and exit propagation with fake site commands, never real Slurm."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def launcher(tmp_path):
    bash = shutil.which("bash")
    if not bash and os.name == "nt" and (git := shutil.which("git")):
        candidate = Path(git).resolve().parent.parent / "bin/bash.exe"
        bash = str(candidate) if candidate.is_file() else None
    if not bash:
        pytest.skip("Bash is needed to exercise the Slurm shell example")

    def shell_path(path):
        return subprocess.check_output(
            [bash, "-c", 'cygpath -u "$1"', "path", str(path)], text=True
        ).strip() if os.name == "nt" else str(path)

    source = Path(__file__).resolve().parents[1] / "scripts/slurm/job.slurm"
    script = tmp_path / "job.slurm"
    content = source.read_text().replace("{{PROJECT_NAME}}", "Example")
    content = content.replace("{{PROJECT_UPPER}}", "EXAMPLE").replace("{{PACKAGE_NAME}}", "example")
    # Git Bash rewrites PATH at startup; install fake commands after that to isolate site calls.
    script.write_text('export PATH="$FAKE_BIN:$PATH"\n' + content, encoding="utf-8", newline="\n")
    data, project, scratch, fakebin = (tmp_path / n for n in ("data", "project", "scratch", "bin"))
    repo = data / "Example"
    runtime = project / "Example/runtimes/image.sif"
    for folder in (repo, runtime.parent, scratch, fakebin):
        folder.mkdir(parents=True, exist_ok=True)
    runtime.touch()
    commands = {
        "module": 'exit 0',
        "git": 'if [ "$1" = rev-parse ]; then printf "revision\\n"; fi',
        "srun": 'exec "$@"',
        "apptainer": 'printf "%s\\n" "$@" >> "$CALL_LOG"\n'
                     '[ "$APPTAINERENV_PYTHONNOUSERSITE" = 1 ] || exit 99\n'
                     'case " $* " in *" -c "*) exit 0;; *) exit 7;; esac',
    }
    for name, body in commands.items():
        path = fakebin / name
        path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
        path.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VSC_", "SLURM_", "APPTAINERENV_"))}
    env.update(VSC_DATA=shell_path(data), VSC_SCRATCH=shell_path(scratch), SLURM_JOB_ID="123",
               SLURM_CPUS_PER_TASK="2", CALL_LOG=shell_path(tmp_path / "calls"),
               FAKE_BIN=shell_path(fakebin))

    def run(image):
        return subprocess.run([bash, shell_path(script), shell_path(repo), shell_path(project),
                               shell_path(image), "revision", "-m", "example"],
                              env=env, capture_output=True, text=True, timeout=15)

    return run, runtime, scratch, tmp_path / "calls"


def test_sif_runs_through_apptainer_and_preserves_failure_workspace(launcher):
    run, runtime, scratch, calls = launcher
    result = run(runtime)
    assert result.returncode == 7, result.stderr
    assert "--cleanenv" in calls.read_text() and "image.sif" in calls.read_text()
    assert len(list((scratch / "Example").glob("123_single_*"))) == 1
    assert "verify publication" in result.stdout


@pytest.mark.parametrize("name", ["python", "missing.sif"])
def test_noncontainer_or_missing_runtime_fails_before_site_commands(launcher, name):
    run, runtime, scratch, calls = launcher
    invalid = runtime.with_name(name)
    if name == "python":
        invalid.touch()
    result = run(invalid)
    assert result.returncode == 2 and "PROJECT .sif container" in result.stderr
    assert not calls.exists() and not list(scratch.iterdir())
