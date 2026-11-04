#!/usr/bin/env python3
"""Loading and merging JSON schemas used to validate Tactus config files."""

import json
import os
from pathlib import Path

from . import GeneralConstants
from .aux_types import QuasiConstant
from .general_utils import merge_dicts
from .path_utils import path_from_subpath


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
    """Return absolute paths for the selected main config schema files."""
    if schema_paths is None:
        schema_paths = ConfigSchemaDefaults.TACTUS_MAIN_CONFIG_JSON_SCHEMA_PATHS
    elif isinstance(schema_paths, (str, Path)):
        schema_paths = str(schema_paths).split(os.pathsep)

    resolved_paths = []
    for schema_path in schema_paths:
        schema_path = Path(schema_path)
        if schema_path.exists():
            resolved_path = schema_path.resolve()
        else:
            # Import here to avoid a module-level cycle: config_parser imports
            # this module.
            from .config_parser import ConfigPaths

            resolved_path = path_from_subpath(
                schema_path, ConfigPaths.SCHEMAS_SEARCHPATHS
            )
        resolved_paths.append(resolved_path.resolve())
    return resolved_paths


def get_main_config_json_schema(schema_paths=None):
    """Load and merge the JSON schemas used to validate a main config file.

    Args:
        schema_paths (list[Path] | None): Schema files to merge in order. If None,
            the minimal Tactus schema and the NWP schema are used.

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


def get_config_schema_paths(config):
    """Return the schema files associated with a parsed config."""
    schema_paths = (config.metadata or {}).get("schema_files")
    return get_main_config_schema_paths(schema_paths)
