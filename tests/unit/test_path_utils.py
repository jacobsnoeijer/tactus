"""Tests for common path resolution helpers."""

import pytest

from tactus.path_utils import path_from_subpath, resolve_file


def test_path_from_subpath_uses_first_search_path(tmp_path):
    high_priority = tmp_path / "high"
    low_priority = tmp_path / "low"
    high_file = high_priority / "nested" / "config.yml"
    low_file = low_priority / "config.yml"
    high_file.parent.mkdir(parents=True)
    low_file.parent.mkdir(parents=True)
    high_file.touch()
    low_file.touch()

    assert path_from_subpath("config.yml", [high_priority, low_priority]) == high_file


def test_path_from_subpath_last_match(tmp_path):
    search_path = tmp_path / "data"
    first_file = search_path / "a" / "schema.json"
    last_file = search_path / "b" / "schema.json"
    first_file.parent.mkdir(parents=True)
    last_file.parent.mkdir(parents=True)
    first_file.touch()
    last_file.touch()

    matches = list(search_path.rglob("**/schema.json"))
    assert path_from_subpath("schema.json", [search_path], last=True) == matches[-1]


def test_resolve_file_prefers_local_file_over_package(tmp_path):
    local_file = tmp_path / "project" / "__init__.py"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("# project file\n", encoding="utf-8")

    with resolve_file(
        "__init__.py", searchpaths=tmp_path / "project", package="tactus"
    ) as path:
        assert path == local_file


def test_resolve_file_falls_back_to_package(tmp_path):
    with resolve_file("__init__.py", searchpaths=tmp_path, package="tactus") as path:
        assert path.name == "__init__.py"
        assert path.is_file()


def test_resolve_file_accepts_absolute_path(tmp_path):
    file_path = tmp_path / "config.yml"
    file_path.touch()

    with resolve_file(file_path) as path:
        assert path == file_path.resolve()


def test_resolve_file_rejects_parent_directory_reference():
    with pytest.raises(ValueError, match="cannot contain"), resolve_file("../config.yml"):
        pass
