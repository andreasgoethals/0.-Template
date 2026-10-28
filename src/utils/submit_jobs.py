"""Submit a reviewed JSON list of sbatch argument lists; preview unless --submit is given.

No running-job pool or injected dependencies. A verified site submission ceiling controls only
queue admission. Run one persistent submitter per plan; accepted IDs survive restarts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

from src.utils.atomic import write_text
from src.utils.paths import REPO_ROOT, manifests_dir


def array_indices(args: list[str]) -> list[int] | None:
    """Preserve original work IDs when an array needs multiple site-admissible submissions."""
    value = next((a.split("=", 1)[1] for a in args if a.startswith("--array=")), None)
    if value is None:
        return None
    if "%" in value and not re.fullmatch(r"[1-9]\d*", value.split("%", 1)[1]):
        raise ValueError("An optional array throttle must be a positive integer.")
    indices = set()
    for part in value.split("%", 1)[0].split(","):
        match = re.fullmatch(r"(\d+)(?:-(\d+)(?::([1-9]\d*))?)?", part)
        if not match:
            raise ValueError(f"Invalid array range: {part}")
        first, last, step = match.groups()
        if int(last or first) < int(first):
            raise ValueError(f"Reversed array range: {part}")
        indices.update(range(int(first), int(last or first) + 1, int(step or 1)))
    return sorted(indices)


def array_tasks(args: list[str]) -> int:
    indices = array_indices(args)
    return len(indices) if indices is not None else 1


def load_plan(path: Path) -> list[list[str]]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, list) or not plan:
        raise ValueError("Plan must be a nonempty list of sbatch argument lists.")
    for args in plan:
        if not isinstance(args, list) or not args or not all(isinstance(a, str) for a in args):
            raise ValueError("Each submission must be an argument list, not a shell command.")
        # Keep cluster/account/QoS scope consistent with the capacity query; do not wait for jobs.
        if any(a in {"-M", "-A", "-q", "-a", "-W", "--wait", "--wrap", "--array"}
               or a.startswith(("-M", "-A", "-q", "--clusters", "--account", "--qos", "--wrap=", "--wait=")) for a in args):
            raise ValueError("Use CLI cluster/account/qos; use --array=RANGE; no --wait/--wrap.")
        if sum(a.startswith("--array=") for a in args) > 1 or any(
            a.startswith("-a") and not a.startswith("--") for a in args
        ):
            raise ValueError("Use at most one --array=RANGE argument.")
        array_tasks(args)
    return plan


def queue_count(scope: list[str]) -> int:
    proc = subprocess.run(["squeue", *scope, "--me", "--noheader", "--array", "--format=%i"],
                          cwd=REPO_ROOT, capture_output=True, text=True, check=True, timeout=30)
    return len(proc.stdout.splitlines())


def submit(plan: list[list[str]], scope: list[str], limit: int, receipt: Path,
           *, poll_seconds: float = 60) -> None:
    """Fill site submission capacity; persist an uncertain state before contacting Slurm."""
    if limit < 1 or poll_seconds < 1:
        raise ValueError("Use a positive site submission ceiling and poll interval.")
    identity = {"plan": plan, "scope": scope, "cwd": str(REPO_ROOT.resolve())}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    lock = receipt.with_suffix(".lock")
    # Exclusive creation also works across submitter processes; stale locks require inspection.
    with lock.open("x", encoding="utf-8") as handle:
        handle.write("One submitter owns this plan. Do not remove while it is running.\n")
    try:
        state = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {
            "identity": identity, "accepted": [], "in_flight": None, "next": 0, "offset": 0,
        }
        if state["identity"] != identity or state["in_flight"] is not None:
            raise RuntimeError("Changed plan or uncertain prior submission; reconcile receipt with Slurm first.")
        for index in range(state["next"], len(plan)):
            while True:
                # A short query outage does not mean the queue is empty.
                try:
                    available = limit - queue_count(scope)
                except (OSError, subprocess.SubprocessError) as exc:
                    print(f"Queue unavailable; no submission: {exc}", flush=True)
                    time.sleep(poll_seconds)
                    continue
                if available < 1:
                    print(f"Waiting for site submission capacity: batch {index}", flush=True)
                    time.sleep(poll_seconds)
                    continue
                indices = array_indices(plan[index])
                remaining = len(indices) - state["offset"] if indices is not None else 1
                if any(a.startswith("--array=") and "%" in a for a in plan[index]):
                    # Splitting would multiply an explicitly requested per-array running limit.
                    if remaining > limit:
                        raise ValueError("Oversized throttled array needs an explicitly reviewed split.")
                    if remaining > available:
                        time.sleep(poll_seconds)
                        continue
                size = min(remaining, available)
                args = list(plan[index])
                if indices is not None and (size < len(indices) or state["offset"]):
                    position = next(i for i, a in enumerate(args) if a.startswith("--array="))
                    throttle = "%" + args[position].split("%", 1)[1] if "%" in args[position] else ""
                    selected = indices[state["offset"]:state["offset"] + size]
                    args[position] = "--array=" + ",".join(map(str, selected)) + throttle
                state["in_flight"] = {"index": index, "offset": state["offset"], "args": args}
                write_text(receipt, json.dumps(state, indent=2))
                proc = subprocess.run(["sbatch", "--parsable", *scope, *args],
                                      cwd=REPO_ROOT, capture_output=True, text=True,
                                      check=False, timeout=60)
                if proc.returncode == 0 and re.fullmatch(r"\d+(?:;[\w.-]+)?", proc.stdout.strip()):
                    state["accepted"].append({"id": proc.stdout.strip(), **state["in_flight"]})
                    state["in_flight"] = None
                    state["offset"] += size
                    complete = size == remaining
                    if complete:
                        state["next"], state["offset"] = index + 1, 0
                    write_text(receipt, json.dumps(state, indent=2))
                    print(f"Accepted {index}: {proc.stdout.strip()}", flush=True)
                    if complete:
                        break
                    continue
                # Only definite capacity refusals are safe to retry; generic QoS errors may be bad resources.
                if proc.returncode and not proc.stdout.strip() and re.search(
                    r"(?:QOS|Assoc).*SubmitJob.*Limit|maximum number of submitted jobs", proc.stderr, re.I
                ):
                    state["in_flight"] = None
                    write_text(receipt, json.dumps(state, indent=2))
                    time.sleep(poll_seconds)
                    continue
                raise RuntimeError(f"Submission not confirmed; inspect receipt and Slurm: {proc.stderr.strip()}")
    finally:
        lock.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--cluster", required=True, choices=("wice", "mindwell"))
    parser.add_argument("--account", required=True)
    parser.add_argument("--qos", required=True)
    parser.add_argument("--site-submit-limit", type=int, required=True,
                        help="verified pending+running ceiling for this user/account/QoS scope")
    parser.add_argument("--poll-seconds", type=float, default=60)
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args(argv)
    plan = load_plan(args.plan)
    scope = [f"--clusters={args.cluster}", f"--account={args.account}", f"--qos={args.qos}"]
    key = hashlib.sha256(json.dumps([plan, scope]).encode()).hexdigest()[:16]
    receipt = manifests_dir() / "submissions" / f"{key}.json"
    print(f"{len(plan)} submissions; receipt: {receipt}")
    if not args.submit:
        print(json.dumps(plan, indent=2))
        return 0
    submit(plan, scope, args.site_submit_limit, receipt, poll_seconds=args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
