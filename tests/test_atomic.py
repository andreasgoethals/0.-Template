# Protect reports from failed replacement; project writers can reuse the same helper.
import pytest

from src.utils import atomic


def test_replace_failure_keeps_previous_file_and_removes_temporary(tmp_path, monkeypatch):
    path = tmp_path / "report.md"
    path.write_text("previous", encoding="utf-8")

    def fail(*args):
        raise OSError("replacement failed")

    monkeypatch.setattr(atomic.os, "replace", fail)
    with pytest.raises(OSError):
        atomic.write_text(path, "new")
    assert path.read_text() == "previous"
    assert list(tmp_path.iterdir()) == [path]


def test_complete_utf8_replacement(tmp_path):
    path = tmp_path / "nested" / "report.md"
    atomic.write_text(path, "résultats\n")
    assert path.read_bytes() == "résultats\n".encode()
