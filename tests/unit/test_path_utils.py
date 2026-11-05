from pathlib import Path

import pytest

from tactus.path_utils import resolve_from_searchpaths, resolve_path


def test_resolve_from_searchpaths_returns_path(tmp_path):
    schema_dir = tmp_path / "schemas"
    schema_file = schema_dir / "nested" / "custom.json"
    schema_file.parent.mkdir(parents=True)
    schema_file.write_text("{}", encoding="utf-8")

    resolved_path = resolve_from_searchpaths("custom.json", [schema_dir])

    assert isinstance(resolved_path, Path)
    assert resolved_path == schema_file.resolve()


def test_resolve_from_searchpaths_uses_first_search_path(tmp_path):
    high_priority = tmp_path / "high"
    low_priority = tmp_path / "low"
    high_file = high_priority / "nested" / "config.yml"
    low_file = low_priority / "config.yml"
    high_file.parent.mkdir(parents=True)
    low_file.parent.mkdir(parents=True)
    high_file.touch()
    low_file.touch()

    assert (
        resolve_from_searchpaths("config.yml", [high_priority, low_priority])
        == high_file.resolve()
    )


def test_resolve_from_searchpaths_last_match(tmp_path):
    search_path = tmp_path / "data"
    first_file = search_path / "a" / "schema.json"
    last_file = search_path / "b" / "schema.json"
    first_file.parent.mkdir(parents=True)
    last_file.parent.mkdir(parents=True)
    first_file.touch()
    last_file.touch()

    matches = list(search_path.rglob("**/schema.json"))
    assert resolve_from_searchpaths("schema.json", [search_path], last=True) == (
        matches[-1].resolve()
    )


def test_resolve_path_checks_relative_file_under_configured_search_paths(
    tmp_path, monkeypatch
):
    schema_root = tmp_path / "schemas"
    schema_file = schema_root / "nested" / "project.json"
    schema_file.parent.mkdir(parents=True)
    schema_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("sys.path", [])

    resolved_path = resolve_path("nested/project.json", searchpaths=[schema_root])

    assert isinstance(resolved_path, Path)
    assert resolved_path == schema_file.resolve()


def test_resolve_path_rejects_ambiguous_matches_across_search_paths(
    tmp_path, monkeypatch
):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "project.json").write_text("{}", encoding="utf-8")
    (second_root / "project.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("sys.path", [])

    with pytest.raises(ValueError, match="Ambiguous path resolution"):
        resolve_path("project.json", searchpaths=[first_root, second_root])


def test_resolve_path_rebases_absolute_path_under_sys_path(tmp_path, monkeypatch):
    requested_root = tmp_path / "requested"
    actual_root = tmp_path / "actual"
    actual_file = actual_root / "configs" / "project.toml"
    actual_file.parent.mkdir(parents=True)
    actual_file.write_text("[general]\ncase = 'demo'\n", encoding="utf-8")
    requested_file = requested_root / "configs" / "project.toml"
    monkeypatch.setattr("sys.path", [str(requested_root), str(actual_root)])

    resolved_path = resolve_path(requested_file)

    assert isinstance(resolved_path, Path)
    assert resolved_path == actual_file.resolve()


def test_resolve_path_can_return_unresolved_path_when_requested(tmp_path, monkeypatch):
    missing_path = tmp_path / "missing.toml"
    monkeypatch.setattr("sys.path", [])

    resolved_path = resolve_path(missing_path, ignore_errors=True)

    assert isinstance(resolved_path, Path)
    assert resolved_path == missing_path.resolve()


def test_resolve_path_ignores_empty_sys_path_entries(tmp_path, monkeypatch):
    requested = tmp_path / "missing" / "config.toml"
    monkeypatch.setattr("sys.path", [""])

    with pytest.raises(FileNotFoundError):
        resolve_path(requested)
