"""Exercise new-project initialization without editing the template checkout."""

import importlib.util
import json
import tomllib
from pathlib import Path

import pytest


def token(name):
    return "{" * 2 + name + "}" * 2


@pytest.fixture
def initializer(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "_template" / "init_project.py"
    if not source.is_file():
        pytest.skip("Initializer removed from this initialized project")
    spec = importlib.util.spec_from_file_location("template_initializer", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    return module


def test_description_round_trips_toml_json_and_prose(initializer, tmp_path):
    description = 'Quoted "research" at C:\\work\nwith a second line'
    placeholder = token("DESCRIPTION")
    (tmp_path / "pyproject.toml").write_text(
        f'description = "{placeholder}"\n', encoding="utf-8"
    )
    (tmp_path / "example.ipynb").write_text(
        json.dumps({"cells": [{"source": [placeholder]}]}), encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(placeholder, encoding="utf-8")
    changed, unknown = initializer.substitute({"DESCRIPTION": description}, dry_run=False)
    assert len(changed) == 3 and not unknown
    assert tomllib.loads((tmp_path / "pyproject.toml").read_text())["description"] == description
    assert json.loads((tmp_path / "example.ipynb").read_text())["cells"][0]["source"] == [description]
    assert (tmp_path / "README.md").read_text() == description


@pytest.mark.parametrize("dry_run", [False, True])
def test_unknown_token_prevents_partial_initialization(initializer, tmp_path, dry_run):
    known = tmp_path / "a.md"
    unknown = tmp_path / "z.md"
    known.write_text(token("PROJECT_NAME"))
    unknown.write_text(token("UNKNOWN_KEY"))
    before = {path: path.read_bytes() for path in (known, unknown)}
    _, leftovers = initializer.substitute({"PROJECT_NAME": "Example"}, dry_run=dry_run)
    assert leftovers
    assert {path: path.read_bytes() for path in before} == before


def test_valid_dry_run_writes_nothing(initializer, tmp_path):
    path = tmp_path / "README.md"
    path.write_text(token("PROJECT_NAME"))
    before = path.read_bytes()
    changed, leftovers = initializer.substitute({"PROJECT_NAME": "Example"}, dry_run=True)
    assert changed == ["README.md"] and not leftovers
    assert path.read_bytes() == before


def test_custom_submodule_nested_repo_and_environment_are_untouched(initializer, tmp_path):
    (tmp_path / ".gitmodules").write_text(
        '[submodule "reference"]\n\tpath = references/custom-library\n'
        '\turl = https://example.invalid/reference.git\n'
    )
    protected = []
    for name, marker in [
        ("references/custom-library", None),
        ("nested-repository", ".git"),
        ("custom-environment", "pyvenv.cfg"),
    ]:
        folder = tmp_path / name
        folder.mkdir(parents=True)
        if marker:
            (folder / marker).touch()
        path = folder / "README.md"
        path.write_text(token("PROJECT_NAME"))
        protected.append(path)
    (tmp_path / "README.md").write_text(token("PROJECT_NAME"))
    changed, leftovers = initializer.substitute({"PROJECT_NAME": "Example"}, dry_run=False)
    assert changed == ["README.md"] and not leftovers
    assert all(path.read_text() == token("PROJECT_NAME") for path in protected)


def test_invalid_structured_output_prevents_all_writes(initializer, tmp_path):
    readme = tmp_path / "a.md"
    readme.write_text(token("PROJECT_NAME"))
    (tmp_path / "broken.toml").write_text(f'name = "{token("PROJECT_NAME")}"\n[broken')
    with pytest.raises(tomllib.TOMLDecodeError):
        initializer.substitute({"PROJECT_NAME": "Example"}, dry_run=False)
    assert readme.read_text() == token("PROJECT_NAME")


def test_unknown_token_is_a_cli_error_even_in_dry_run(initializer, tmp_path, monkeypatch):
    doc = tmp_path / "docs" / "TEMPLATE.md"
    doc.parent.mkdir()
    doc.write_text(token("UNKNOWN_KEY"))
    monkeypatch.setattr(initializer, "TEMPLATE_DOC", doc)
    assert initializer.main(["Example", "--dry-run"]) == 1
