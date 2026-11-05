"""Shared config, schema, and config-data path policies.

This module owns the search-path configuration used by both the loaders and CLI
inspection commands. Generic filesystem mechanics live in :mod:`path_utils`.
"""

import json
import os
from pathlib import Path

from . import GeneralConstants
from .logs import logger
from .path_utils import resolve_path


class ConfigPathDefaults:
    """Filesystem and schema defaults used throughout Tactus."""

    DATA_DIRECTORY = GeneralConstants.PACKAGE_DIRECTORY / "data"
    CONFIG_DIRECTORY = DATA_DIRECTORY / "config_files"
    INCLUDE_DIRECTORY = CONFIG_DIRECTORY / "include"
    SCHEMAS_DIRECTORY = CONFIG_DIRECTORY / "config_file_schemas"

    PACKAGE_CONFIG_FILE = (CONFIG_DIRECTORY / "config.toml").resolve(strict=True)
    MINIMAL_CONFIG_JSON_SCHEMA_PATH = SCHEMAS_DIRECTORY / "minimal_config_schema.json"
    NWP_CONFIG_JSON_SCHEMA_PATH = SCHEMAS_DIRECTORY / "nwp_config_schema.json"
    TACTUS_MAIN_CONFIG_JSON_SCHEMA_PATHS = (
        MINIMAL_CONFIG_JSON_SCHEMA_PATH,
        NWP_CONFIG_JSON_SCHEMA_PATH,
    )

    try:
        DEFAULT_CONFIG_FILE = Path(os.getenv("TACTUS_CONFIG_PATH", "config.toml"))
        DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_FILE.resolve(strict=True)
    except FileNotFoundError:
        DEFAULT_CONFIG_FILE = PACKAGE_CONFIG_FILE


def _get_searchpaths(env_var, default_path):
    """Get an ordered search path from an environment variable and default."""
    env_paths = os.getenv(env_var)
    searchpaths = env_paths.split(os.pathsep) if env_paths else []
    erroneous_paths = [path for path in searchpaths if not os.path.isabs(path)]
    if erroneous_paths:
        raise RuntimeError(f"{env_var} is not absolute: {erroneous_paths}")
    searchpaths.append(default_path)
    return searchpaths


class ConfigPaths:
    """Centralized path policies for config data, config files, and schemas."""

    CONFIG_DATA_SEARCHPATHS = _get_searchpaths(
        "TACTUS_CONFIG_DATA_DIR", ConfigPathDefaults.DATA_DIRECTORY
    )
    SCHEMAS_SEARCHPATHS = _get_searchpaths(
        "TACTUS_SCHEMAS_DIR", ConfigPathDefaults.SCHEMAS_DIRECTORY
    )

    @staticmethod
    def _prepend_search_paths(searchpaths, paths):
        """Prepend directories, preserving order and avoiding duplicates."""
        if isinstance(paths, (str, Path)):
            paths = [paths]

        existing_paths = {Path(path).resolve() for path in searchpaths}
        new_paths = []
        for path in paths:
            resolved_path = Path(path).expanduser().resolve()
            if resolved_path not in existing_paths:
                new_paths.append(str(resolved_path))
                existing_paths.add(resolved_path)
        searchpaths[:0] = new_paths

    @classmethod
    def add_config_data_dirs(cls, paths):
        """Add directories to the config-data search path."""
        cls._prepend_search_paths(cls.CONFIG_DATA_SEARCHPATHS, paths)

    @classmethod
    def add_schema_dirs(cls, paths):
        """Add directories to the schema search path."""
        cls._prepend_search_paths(cls.SCHEMAS_SEARCHPATHS, paths)

    @staticmethod
    def resolve_config_file(path) -> Path:
        """Resolve an explicit config file with the shared path policy."""
        return resolve_path(path)

    @staticmethod
    def resolve_schema_file(path) -> Path:
        """Resolve a schema using the config-file policy plus schema search roots.

        Configured schema directories are checked before the common ``sys.path``
        package roots. Paths beneath those directories are specified relative to
        the directory (for example ``project/schema.json``).
        """
        return resolve_path(path, searchpaths=ConfigPaths.SCHEMAS_SEARCHPATHS)

    @staticmethod
    def print(config_file=None, host=None):
        """Print available config directories and config-specific include paths."""
        # Local import avoids a cycle: config_parser itself uses ConfigPaths.
        from .config_parser import BasicConfig

        def path_info(list_paths, dirmap=None):
            mapping = {}
            dirmap = dirmap or {}
            for dir_ in list_paths:
                rdir = dirmap.get(dir_, dir_)
                mapping[dir_] = []
                pattern = f"**/{rdir}"

                for searchpath in ConfigPaths.CONFIG_DATA_SEARCHPATHS:
                    results = list(Path(searchpath).rglob(pattern))
                    if len(results) == 1:
                        mapping[dir_].append(str(results[0]))
                    if len(results) > 1:
                        logger.error("Multiple matches found for subpath: {}", searchpath)
                        logger.error("Results: {}", results)
                        raise RuntimeError
            return mapping

        dirmap = {}
        list_paths = ["config_files", "namelist_generation_input", "input"]
        list_config_paths = []
        raw_config = BasicConfig.from_file(config_file)
        for key, value in raw_config.get("include", {}).items():
            section_key = f"config_file_{key}_section"
            resolved_value = value.replace("@HOST@", host) if host is not None else value
            dirmap[section_key] = resolved_value
            if section_key not in list_paths:
                list_config_paths.append(section_key)

        path_info_main = path_info(list_paths, dirmap)
        path_info_config = path_info(list_config_paths, dirmap)

        logger.info("tactus paths for host={}", host)
        logger.info(" Package directory: {}", GeneralConstants.PACKAGE_DIRECTORY)
        logger.info(
            " Config data searchpaths: {}",
            [str(path) for path in ConfigPaths.CONFIG_DATA_SEARCHPATHS],
        )
        logger.info(
            " Schema searchpaths: {}",
            [str(path) for path in ConfigPaths.SCHEMAS_SEARCHPATHS],
        )
        logger.info(
            " Data paths in search order: {}", json.dumps(path_info_main, indent=4)
        )
        logger.info(
            " Config file include paths in search order: {}",
            json.dumps(path_info_config, indent=4),
        )
