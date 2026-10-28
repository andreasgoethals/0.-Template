# Cleanup regression tests protect deletion boundaries and preview behavior.
# A wipe leaves the tracked
# `.gitkeep` markers and their directories behind — without them a fresh clone has nowhere to write.
"""`src/utils/clean_run.py` — the wipe."""

from __future__ import annotations

import subprocess
import sys

import pytest

from src.utils import clean_run


def test_lists_by_default_and_deletes_only_when_asked(isolated_output, capsys) -> None:
    """A listing you meant as a deletion costs one more command; the reverse costs the run."""
    from src.utils.paths import logs_dir

    logs_dir().mkdir(parents=True, exist_ok=True)
    victim = logs_dir() / "run.log"
    victim.write_text("x" * 100, encoding="utf-8")

    clean_run.main([])
    assert victim.exists(), "the default must not delete anything"
    assert "Nothing was deleted" in capsys.readouterr().out

    clean_run.main(["--clean"])
    assert not victim.exists()


def test_a_wipe_keeps_the_directory_skeleton(isolated_output) -> None:
    """`rmtree` would take `output/figures/.gitkeep` with it, and the next clone would have
    nowhere to write."""
    from src.utils.paths import figures_dir, logs_dir

    for folder in (logs_dir(), figures_dir()):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").write_text("", encoding="utf-8")
    per_notebook = figures_dir("nb")
    per_notebook.mkdir(parents=True, exist_ok=True)
    (per_notebook / "01_x.pdf").write_bytes(b"%PDF")
    (logs_dir() / "run.log").write_text("x", encoding="utf-8")

    removed = clean_run.wipe(clean_run.roots()[0])
    assert removed == 2                                  # the pdf and the log, not the markers
    assert (logs_dir() / ".gitkeep").is_file()
    assert (figures_dir() / ".gitkeep").is_file()
    assert not per_notebook.exists()                     # per-run, no marker, so it goes


def test_gitkeep_is_never_counted(isolated_output) -> None:
    """A directory holding only structure markers is already clean."""
    from src.utils.paths import logs_dir

    logs_dir().mkdir(parents=True, exist_ok=True)
    (logs_dir() / ".gitkeep").write_text("", encoding="utf-8")
    assert clean_run.measure(clean_run.roots()[0]) == (0, 0)


def test_both_storage_tiers_are_cleared_on_the_cluster(isolated_output) -> None:
    """All experiments on both tiers must be cleared, while checkpoints remain protected."""
    from src.utils.paths import checkpoints_dir, logs_dir, results_dir

    roots = clean_run.roots()
    assert len(roots) == 2
    assert any("staging" in str(r) for r in roots)
    victims = []
    for experiment in ("experiment0/0a", "experiment1"):
        for path in (
            logs_dir(experiment) / "run.log",
            results_dir("scores.csv", experiment=experiment),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated")
            victims.append(path)
    checkpoint = checkpoints_dir("retained.bin")
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text("expensive")
    for root in roots:
        clean_run.wipe(root)
    assert all(not path.exists() for path in victims)
    assert checkpoint.read_text() == "expensive"


def test_processed_is_opt_in(isolated_output) -> None:
    """Rebuilding the cache can cost far more than re-running the notebooks, so "clean the last
    run" must not silently throw it away."""
    from src.utils.paths import processed_dir

    assert processed_dir() not in clean_run.roots()
    assert processed_dir() in clean_run.roots(processed=True)


def test_project_storage_output_beyond_results_is_cleared(isolated_output):
    root = clean_run.roots()[1]
    (root / "logs").mkdir(parents=True)
    (root / "logs" / "old.log").write_text("old")
    assert clean_run.wipe(root) == 1


def test_unregistered_root_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Not a cleanup target"):
        clean_run.wipe(tmp_path)


def test_linked_directory_is_refused_before_any_deletion(isolated_output):
    root = clean_run.roots()[0]
    root.mkdir(parents=True)
    victim = root / "ordinary.txt"
    victim.write_text("keep until preflight completes")
    outside = isolated_output / "outside"
    outside.mkdir()
    (outside / "precious.txt").write_text("preserve")
    link = root / "linked"
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                       check=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match="linked path"):
            clean_run.wipe(root)
        assert victim.exists()
        assert (outside / "precious.txt").exists()
    finally:
        # Remove only the junction/link itself, never recurse through it.
        if sys.platform == "win32":
            link.rmdir()
        else:
            link.unlink()
