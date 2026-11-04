"""Tests for loading and combining main configuration schemas."""

import json
from pathlib import Path

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


def test_main_schema_files_are_not_meta_validated(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{"type": "not-a-json-schema-type"}', encoding="utf-8")

    assert get_main_config_json_schema([schema_path]) == {
        "type": "not-a-json-schema-type"
    }


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


def test_add_numbers_project_resolves_assemble_config_and_schema_files(
    tmp_path, monkeypatch
):
    """Project-local assemble and schema files use the common path lookup."""
    project_root = tmp_path / "addNumbers"
    data_dir = project_root / "tactus_data"
    assemble_dir = data_dir / "namelist_generation_input" / "CY50t2"
    assemble_dir.mkdir(parents=True)
    assemble_file = assemble_dir / "assemble_addNumbers.yml"
    assemble_file.write_text("sum: [left, right]\n", encoding="utf-8")

    schemas_dir = project_root / "schemas" / "nested"
    schemas_dir.mkdir(parents=True)
    schema_file = schemas_dir / "addNumbers_schema.json"
    schema_file.write_text(
        json.dumps({"type": "object", "properties": {"left": {"type": "integer"}}}),
        encoding="utf-8",
    )
    section_schema_file = schemas_dir / "addNumbers_section_schema.json"
    section_schema_file.write_text(json.dumps({"type": "object"}), encoding="utf-8")

    monkeypatch.setattr(ConfigPaths, "CONFIG_DATA_SEARCHPATHS", [data_dir])
    monkeypatch.setattr(ConfigPaths, "SCHEMAS_SEARCHPATHS", [project_root / "schemas"])

    assert _resolve_namelist_path(
        "namelist_generation_input/CY50t2/assemble_addNumbers.yml"
    ) == assemble_file
    assert get_main_config_schema_paths("addNumbers_schema.json") == [
        schema_file.resolve()
    ]
    assert get_main_config_json_schema("addNumbers_schema.json")["properties"][
        "left"
    ] == {"type": "integer"}
    section_schema = _get_all_json_schemas(
        {"properties": {}}, [project_root / "schemas"]
    )
    assert section_schema["properties"]["addNumbers"] == {
        "$ref": f"file:{section_schema_file}"
    }
