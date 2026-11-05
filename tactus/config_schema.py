#!/usr/bin/env python3
"""Loading and merging JSON schemas used to validate Tactus config files."""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from .config_paths import ConfigPathDefaults, ConfigPaths
from .general_utils import merge_dicts


def get_main_config_schema_paths(schema_paths=None):
    """Return absolute paths for the selected main config schema files."""
    if schema_paths is None:
        schema_paths = os.getenv("TACTUS_SCHEMA_PATH")
        if schema_paths:
            schema_paths = schema_paths.split(os.pathsep)
        else:
            schema_paths = ConfigPathDefaults.TACTUS_MAIN_CONFIG_JSON_SCHEMA_PATHS
    elif isinstance(schema_paths, (str, Path)):
        schema_paths = [schema_paths]

    return [ConfigPaths.resolve_schema_file(schema) for schema in schema_paths]


def _merge_schema_files(schema_paths):
    """Load and merge already-resolved schema files in the supplied order."""
    json_schema = {}
    for schema_path in schema_paths:
        with Path(schema_path).open(encoding="utf-8") as schema_file:
            json_schema = merge_dicts(
                json_schema,
                json.load(schema_file),
                overwrite=True,
            )
    return json_schema


def get_main_config_json_schema(schema_paths=None):
    """Load and merge the JSON schemas used to validate a main config file.

    Args:
        schema_paths (str | Path | list[str | Path] | None): Schema files to merge
            in order. If None, ``TACTUS_SCHEMA_PATH`` is used when set; otherwise
            the default tactus schema will be used.

    Returns:
        dict: The merged JSON schema.
    """
    return _merge_schema_files(get_main_config_schema_paths(schema_paths))


def assemble_json_schema(json_schema):
    """Return an assembled schema and its source files, when applicable.

    A mapping is treated as an already assembled schema. Otherwise, the input
    is interpreted as one or more schema file paths and merged in order.
    """
    if isinstance(json_schema, Mapping):
        return json_schema, None

    if json_schema is not None and not isinstance(json_schema, (str, Path, list, tuple)):
        raise TypeError("json_schema must be a schema dictionary or file path(s).")

    if isinstance(json_schema, (list, tuple)) and not all(
        isinstance(schema_file, (str, Path)) for schema_file in json_schema
    ):
        raise TypeError("json_schema must be a schema dictionary or file path(s).")

    schema_paths = get_main_config_schema_paths(json_schema)
    return _merge_schema_files(schema_paths), schema_paths


def get_config_schema_paths(config):
    """Return the schema files associated with a parsed config."""
    schema_paths = (config.metadata or {}).get("schema_files")
    return get_main_config_schema_paths(schema_paths)
