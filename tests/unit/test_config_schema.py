"""Tests for loading and combining main configuration schemas."""

import json
import os
from pathlib import Path

import pytest

import tactus.__main__ as tactus_main
import tactus.argparse_wrapper as argparse_wrapper
from tactus.argparse_wrapper import get_args_parser
from tactus.config_parser import ConfigPaths, _get_all_json_schemas
from tactus.config_schema import (
    get_main_config_json_schema,
    get_main_config_schema_paths,
)
from tactus.namelist import _resolve_namelist_path


def test_main_config_schemas_are_merged_in_order(tmp_path):
    base_schema = {
        "type": "object",
        "properties": {"general": {"$ref": "#/definitions/general"}},
        "required": ["general"],
        "definitions": {
            "general": {
                "type": "object",
                "properties": {"case": {"type": "string"}},
                "required": ["case"],
            }
        },
    }
    project_schema = {
        "type": "object",
        "properties": {
            "myinput": {
                "type": "object",
                "properties": {"a": {"type": "integer"}},
                "required": ["a"],
            }
        },
        "required": ["myinput"],
    }
    schema_paths = []
    for name, schema in (("base.json", base_schema), ("project.json", project_schema)):
        schema_path = tmp_path / name
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        schema_paths.append(schema_path)

    merged_schema = get_main_config_json_schema(schema_paths)

    assert merged_schema["required"] == ["general", "myinput"]
    assert merged_schema["definitions"]["general"]["required"] == ["case"]
    assert merged_schema["properties"]["myinput"]["required"] == ["a"]


def test_schema_cli_accepts_a_list_of_files():
    args = get_args_parser().parse_args([
        "start",
        "suite",
        "--config-file",
        "project.toml",
        "--schema",
        "minimal.json",
        "project.json",
    ])

    assert args.schema == [Path("minimal.json"), Path("project.json")]


def test_schema_cli_can_be_repeated():
    args = get_args_parser().parse_args([
        "start",
        "suite",
        "--config-file",
        "project.toml",
        "--schema",
        "minimal.json",
        "--schema",
        "project.json",
        "scheduler.json",
    ])

    assert args.schema == [
        Path("minimal.json"),
        Path("project.json"),
        Path("scheduler.json"),
    ]


def test_explicit_schema_paths_override_environment(tmp_path, monkeypatch):
    env_schema = tmp_path / "env_schema.json"
    explicit_schema = tmp_path / "explicit_schema.json"
    env_schema.write_text("{}", encoding="utf-8")
    explicit_schema.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("TACTUS_SCHEMA_PATH", str(env_schema))

    assert get_main_config_schema_paths([explicit_schema]) == [
        explicit_schema.resolve()
    ]


def test_missing_selected_schema_raises_lookup_error(tmp_path, monkeypatch):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    monkeypatch.setattr(ConfigPaths, "SCHEMAS_SEARCHPATHS", [schema_dir])

    with pytest.raises(RuntimeError, match="Could not find missing_schema.json"):
        get_main_config_schema_paths(["missing_schema.json"])


