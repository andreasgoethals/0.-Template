"""Real local Git fixtures verify pin isolation; no remote network is used."""

import subprocess

import pytest

from src.utils import update_library


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


@pytest.fixture
def library_pair(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")
    upstream = tmp_path / "upstream"
    parent = tmp_path / "consumer"
    for root in (upstream, parent):
        root.mkdir()
        git(root, "init", "-b", "main")
        git(root, "config", "user.name", "Fixture")
        git(root, "config", "user.email", "fixture@example.invalid")
    (upstream / "reference.md").write_text("first revision")
    git(upstream, "add", "reference.md")
    git(upstream, "commit", "-m", "Initial reference")
    git(parent, "submodule", "add", str(upstream), "vsc-library")
    git(parent, "commit", "-am", "Register reference")
    (upstream / "reference.md").write_text("second revision")
    git(upstream, "commit", "-am", "Update reference")
    monkeypatch.setattr(update_library, "REPO_ROOT", parent)
    monkeypatch.setattr(update_library, "SUBMODULE", "vsc-library")
    return parent, upstream


def test_pin_commit_preserves_unrelated_staged_work(library_pair):
    parent, upstream = library_pair
    (parent / "unrelated.txt").write_text("owner's pending change")
    git(parent, "add", "unrelated.txt")
    assert update_library.main(["--update", "--commit"]) == 0
    assert git(parent, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == "vsc-library"
    assert git(parent, "diff", "--cached", "--name-only") == "unrelated.txt"
    assert git(parent / "vsc-library", "rev-parse", "HEAD") == git(upstream, "rev-parse", "HEAD")


def test_dirty_library_is_preserved(library_pair):
    parent, _ = library_pair
    library = parent / "vsc-library"
    before = git(library, "rev-parse", "HEAD")
    (library / "reference.md").write_text("uncommitted local edit")
    with pytest.raises(RuntimeError, match="preserve its local changes"):
        update_library.main(["--update"])
    assert git(library, "rev-parse", "HEAD") == before
    assert (library / "reference.md").read_text() == "uncommitted local edit"


def test_uninitialized_library_gets_initialization_advice(library_pair, capsys):
    parent, _ = library_pair
    git(parent, "submodule", "deinit", "vsc-library")
    assert update_library.main(["--update"]) == 1
    assert "git submodule update --init -- vsc-library" in capsys.readouterr().out
