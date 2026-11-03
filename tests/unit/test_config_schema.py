"""Tests for loading and combining main configuration schemas."""

import json
from pathlib import Path

from tactus.argparse_wrapper import get_args_parser
from tactus.config_schema import (
    ConfigSchemaDefaults,
    get_main_config_json_schema,
    get_main_config_schema_paths,
)


def test_default_main_config_schema_stack_contains_minimal_and_nwp():
    assert get_main_config_schema_paths() == [
        ConfigSchemaDefaults.MINIMAL_MAIN_CONFIG_JSON_SCHEMA_PATH.resolve(),
        ConfigSchemaDefaults.NWP_MAIN_CONFIG_JSON_SCHEMA_PATH.resolve(),
    ]


def test_main_config_schemas_are_merged_in_order(tmp_path):
    base_schema = {
        "type": "object",
        "properties": {
            "general": {
                "$ref": "#/definitions/general"
            }
        },
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


def test_main_schema_files_are_not_meta_validated(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{"type": "not-a-json-schema-type"}', encoding="utf-8")

    assert get_main_config_json_schema([schema_path]) == {
        "type": "not-a-json-schema-type"
    }


def test_schema_cli_accepts_a_list_of_files():
    args = get_args_parser().parse_args(
        [
            "start",
            "suite",
            "--config-file",
            "project.toml",
            "--schema",
            "minimal.json",
            "project.json",
        ]
    )

    assert args.schema == [Path("minimal.json"), Path("project.json")]


def test_schema_cli_can_be_repeated():
    args = get_args_parser().parse_args(
        [
            "start",
            "suite",
            "--config-file",
            "project.toml",
            "--schema",
            "minimal.json",
            "--schema",
            "project.json",
            "scheduler.json",
        ]
    )

    assert args.schema == [
        Path("minimal.json"),
        Path("project.json"),
        Path("scheduler.json"),
    ]
