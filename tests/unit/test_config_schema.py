"""Tests for loading and combining main configuration schemas."""

import json
from pathlib import Path

import pytest

from tactus.argparse_wrapper import get_args_parser
from tactus.config_parser import ParsedConfig
from tactus.config_paths import ConfigPaths
from tactus.config_schema import (
    get_main_config_json_schema,
    get_main_config_schema_paths,
)


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

    assert get_main_config_schema_paths([explicit_schema]) == [explicit_schema.resolve()]


def test_missing_selected_schema_raises_lookup_error(tmp_path, monkeypatch):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    monkeypatch.setattr(ConfigPaths, "SCHEMAS_SEARCHPATHS", [schema_dir])

    with pytest.raises(FileNotFoundError, match="missing_schema.json"):
        get_main_config_schema_paths(["missing_schema.json"])


def test_parsed_config_from_file_accepts_schema_file_list(tmp_path, monkeypatch):
    schema_dir = tmp_path / "schemas"
    nested_schema_dir = schema_dir / "project"
    nested_schema_dir.mkdir(parents=True)
    base_schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "object",
                "properties": {
                    "key1": {
                        "type": "object",
                        "properties": {
                            "sub1": {"type": "integer"},
                            "sub2": {"type": "integer"},
                        },
                    }
                },
            }
        },
    }
    project_schema = {
        "properties": {
            "a": {
                "properties": {
                    "key1": {
                        "properties": {
                            "sub2": {"type": "number"},
                            "sub3": {"type": "integer"},
                        }
                    },
                    "key2": {"type": "integer"},
                }
            }
        }
    }
    schema_files = [
        schema_dir / "base.json",
        nested_schema_dir / "project.json",
    ]
    for schema_file, schema in zip(schema_files, (base_schema, project_schema)):
        schema_file.write_text(json.dumps(schema), encoding="utf-8")

    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "a": {
                "key1": {"sub1": 1, "sub2": 22, "sub3": 3},
                "key2": 2,
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(ConfigPaths, "SCHEMAS_SEARCHPATHS", [schema_dir])

    config = ParsedConfig.from_file(
        config_file, json_schema=["base.json", "project/project.json"]
    )

    assert config["a.key1"] == {"sub1": 1, "sub2": 22, "sub3": 3}
    assert config["a.key2"] == 2
    assert config.metadata["schema_files"] == [
        str(schema_file.resolve()) for schema_file in schema_files
    ]
    merged_schema = json.loads(config.json_schema.dumps(style="json"))
    assert merged_schema["properties"]["a"]["properties"]["key1"]["properties"] == {
        "sub1": {"type": "integer"},
        "sub2": {"type": "number"},
        "sub3": {"type": "integer"},
    }


def test_parsed_config_from_file_accepts_single_schema_path(tmp_path, monkeypatch):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    schema_file = schema_dir / "project.json"
    schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    config_file = tmp_path / "config.json"
    config_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ConfigPaths, "SCHEMAS_SEARCHPATHS", [schema_dir])

    config = ParsedConfig.from_file(config_file, json_schema="project.json")

    assert config.metadata["schema_files"] == [str(schema_file.resolve())]
