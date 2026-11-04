#!/usr/bin/env python3
"""Loading and merging JSON schemas used to validate Tactus config files."""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from . import GeneralConstants
from .aux_types import QuasiConstant
from .general_utils import merge_dicts


class ConfigSchemaDefaults(QuasiConstant):
    """Defaults related to config JSON schemas."""

    SCHEMAS_DIRECTORY = (
        GeneralConstants.PACKAGE_DIRECTORY / "data/config_files/config_file_schemas"
    )
    MINIMAL_CONFIG_JSON_SCHEMA_PATH = SCHEMAS_DIRECTORY / "minimal_config_schema.json"
    NWP_CONFIG_JSON_SCHEMA_PATH = SCHEMAS_DIRECTORY / "nwp_config_schema.json"

    TACTUS_MAIN_CONFIG_JSON_SCHEMA_PATHS = (
        MINIMAL_CONFIG_JSON_SCHEMA_PATH,
        NWP_CONFIG_JSON_SCHEMA_PATH,
    )


def get_main_config_schema_paths(schema_paths=None):
    """Return absolute paths for the selected main config schema files.

    ``schema_paths`` may be one path or a list of paths. When it is ``None``,
    ``TACTUS_SCHEMA_PATH`` can select one or more files; otherwise the packaged
    main config schemas are used.
    """
    if schema_paths is None:
        schema_paths = os.getenv("TACTUS_SCHEMA_PATH")
        if schema_paths:
            schema_paths = schema_paths.split(os.pathsep)
        else:
            schema_paths = ConfigSchemaDefaults.TACTUS_MAIN_CONFIG_JSON_SCHEMA_PATHS
    elif isinstance(schema_paths, (str, Path)):
        schema_paths = [schema_paths]

    resolved_paths = []
    for schema in schema_paths:
        schema_path = Path(schema)
        if schema_path.exists():
            resolved_path = schema_path.resolve()
        else:
            # Import here to avoid a module-level cycle: config_parser imports
            # this module.
            from .config_parser import ConfigPaths

            resolved_path = ConfigPaths.schema_path_from_subpath(schema_path)
        resolved_paths.append(resolved_path.resolve())
    return resolved_paths


def get_main_config_json_schema(schema_paths=None):
    """Load and merge the JSON schemas used to validate a main config file.

    Args:
        schema_paths (str | Path | list[str | Path] | None): Schema files to merge
            in order. If None, ``TACTUS_SCHEMA_PATH`` is used when set; otherwise
            the default tactus schema will be used.

    Returns:
        dict: The merged JSON schema.
    """
    schema_paths = get_main_config_schema_paths(schema_paths)

    json_schema = {}
    for schema_path in schema_paths:
        with Path(schema_path).open(encoding="utf-8") as schema_file:
            json_schema = merge_dicts(
                json_schema,
                json.load(schema_file),
                overwrite=True,
            )

    return json_schema


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
    return get_main_config_json_schema(schema_paths), schema_paths


def get_config_schema_paths(config):
    """Return the schema files associated with a parsed config."""
    schema_paths = (config.metadata or {}).get("schema_files")
    return get_main_config_schema_paths(schema_paths)
