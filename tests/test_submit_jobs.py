"""Mock Slurm: fill site capacity without throttling running work; retain IDs and stop on ambiguity."""

import json
import subprocess

import pytest

from src.utils import submit_jobs as sj


@pytest.fixture
def scheduler(monkeypatch):
    calls = []
    sleeps = []

    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, f"{100 + len(calls)};wice\n", "")

    monkeypatch.setattr(sj.subprocess, "run", run)
    monkeypatch.setattr(sj.time, "sleep", sleeps.append)
    monkeypatch.setattr(sj, "queue_count", lambda scope: 0)
    return calls, sleeps


def test_all_ready_jobs_submit_without_a_running_cap(tmp_path, scheduler):
    calls, sleeps = scheduler
    plan = [["--array=0-9", "job.slurm", str(i)] for i in range(12)]
    receipt = tmp_path / "receipt.json"
    sj.submit(plan, ["--clusters=wice"], 200, receipt)
    assert len(calls) == 12 and not sleeps
    assert all("--array=0-9" in call for call in calls)
    assert all(not any("%" in arg or "dependency" in arg or "--wait" in arg for arg in call)
               for call in calls)
    sj.submit(plan, ["--clusters=wice"], 200, receipt)
    assert len(calls) == 12  # Restarting an accepted plan must not duplicate jobs.


def test_capacity_refills_and_queue_outages_never_mean_empty(tmp_path, scheduler, monkeypatch):
    calls, sleeps = scheduler
    counts = iter([subprocess.TimeoutExpired("squeue", 30), 4, 2, 3, 0])

    def count(scope):
        result = next(counts)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(sj, "queue_count", count)
    sj.submit([["--array=0-1", "job.slurm"], ["--array=2-3", "job.slurm"]], [], 4,
              tmp_path / "receipt.json")
    assert [sj.array_indices(call) for call in calls] == [[0, 1], [2], [3]]
    assert sleeps == [60, 60]


def test_capacity_refusal_is_retried_but_not_generic_qos_failure(tmp_path, scheduler, monkeypatch):
    answers = iter([
        subprocess.CompletedProcess([], 1, "", "QOSMaxSubmitJobPerUserLimit"),
        subprocess.CompletedProcess([], 0, "123", ""),
    ])
    monkeypatch.setattr(sj.subprocess, "run", lambda *a, **k: next(answers))
    sj.submit([["job.slurm"]], [], 4, tmp_path / "receipt.json")
    assert scheduler[1] == [60]


@pytest.mark.parametrize("failure", [
    subprocess.TimeoutExpired("sbatch", 60),
    subprocess.CompletedProcess([], 0, "unparseable acknowledgement", ""),
    subprocess.CompletedProcess([], 1, "", "Job violates accounting/QOS policy (job submit limit, user's size and/or time limits)"),
])
def test_uncertain_submission_cannot_be_retried_on_restart(tmp_path, scheduler, monkeypatch, failure):
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(sj.subprocess, "run", run)
    receipt = tmp_path / "receipt.json"
    for _ in range(2):
        with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
            sj.submit([["job.slurm"]], [], 4, receipt)
    assert len(calls) == 1
    assert json.loads(receipt.read_text())["in_flight"]["index"] == 0


def test_a_changed_plan_and_concurrent_submitter_are_refused(tmp_path, scheduler):
    receipt = tmp_path / "receipt.json"
    sj.submit([["job.slurm", "first"]], [], 4, receipt)
    with pytest.raises(RuntimeError, match="Changed plan"):
        sj.submit([["job.slurm", "second"]], [], 4, receipt)
    receipt.with_suffix(".lock").touch()
    with pytest.raises(FileExistsError):
        sj.submit([["job.slurm", "first"]], [], 4, receipt)


def test_array_count_and_explicit_throttle(tmp_path, scheduler):
    assert sj.array_tasks(["--array=0-8:2,10%2"]) == 6
    sj.submit([["--array=0-8:2,10%2", "job.slurm"]], [], 6, tmp_path / "receipt.json")
    assert "--array=0-8:2,10%2" in scheduler[0][0]


def test_large_array_splits_into_available_slots_without_changing_work_ids(tmp_path, scheduler, monkeypatch):
    counts = iter([3, 4, 2, 0, 0])
    monkeypatch.setattr(sj, "queue_count", lambda scope: next(counts))
    sj.submit([["--array=5-12", "job.slurm"]], [], 4, tmp_path / "receipt.json")
    calls, sleeps = scheduler
    assert sleeps == [60]
    submitted = [sj.array_indices(call) for call in calls]
    assert submitted == [[5], [6, 7], [8, 9, 10, 11], [12]]
    assert json.loads((tmp_path / "receipt.json").read_text())["next"] == 1


def test_partial_array_resume_keeps_accepted_tasks(tmp_path, scheduler, monkeypatch):
    counts = iter([2, KeyboardInterrupt()])

    def count(scope):
        value = next(counts)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(sj, "queue_count", count)
    receipt = tmp_path / "receipt.json"
    with pytest.raises(KeyboardInterrupt):
        sj.submit([["--array=0-5", "job.slurm"]], [], 4, receipt)
    monkeypatch.setattr(sj, "queue_count", lambda scope: 0)
    sj.submit([["--array=0-5", "job.slurm"]], [], 4, receipt)
    assert [sj.array_indices(call) for call in scheduler[0]] == [[0, 1], [2, 3, 4, 5]]


def test_explicit_throttle_is_not_multiplied_by_splitting(tmp_path, scheduler):
    with pytest.raises(ValueError, match="reviewed split"):
        sj.submit([["--array=0-9%2", "job.slurm"]], [], 4, tmp_path / "receipt.json")
    assert not scheduler[0]


def test_preview_has_no_scheduler_or_receipt_side_effects(tmp_path, scheduler, monkeypatch):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([["job.slurm"]]))
    monkeypatch.setattr(sj, "manifests_dir", lambda: tmp_path / "manifests")
    assert sj.main([str(plan), "--cluster", "wice", "--account", "research", "--qos", "normal",
                    "--site-submit-limit", "100"]) == 0
    assert not scheduler[0] and not (tmp_path / "manifests").exists()


def test_genuine_dependencies_and_resources_are_preserved(tmp_path, scheduler):
    args = ["--dependency=afterok:42", "--cpus-per-task=3", "--mem=8G", "job.slurm"]
    sj.submit([args], [], 100, tmp_path / "receipt.json")
    assert scheduler[0] == [["sbatch", "--parsable", *args]]


def test_queue_query_expands_array_elements_and_uses_the_same_scope(monkeypatch):
    scope = ["--clusters=wice", "--account=research", "--qos=normal"]

    def run(args, **kwargs):
        assert args == ["squeue", *scope, "--me", "--noheader", "--array", "--format=%i"]
        return subprocess.CompletedProcess(args, 0, "12_0\n12_1\n13\n", "")

    monkeypatch.setattr(sj.subprocess, "run", run)
    assert sj.queue_count(scope) == 3
