#!/usr/bin/env python3
"""Program's entry point."""

import contextlib
import datetime
import os
import sys

from . import GeneralConstants
from .argparse_wrapper import get_args_parser
from .config_parser import ConfigPaths, ParsedConfig
from .config_schema import get_main_config_json_schema, get_main_config_schema_paths
from .host_actions import TactusHost
from .logs import LoggerHandlers, log_elapsed_time, logger

# Enable logger if the project is being used as an application
logger.enable(GeneralConstants.PACKAGE_NAME)


@log_elapsed_time()
def main(argv=None):
    """Program's main routine."""
    if argv is None:
        argv = sys.argv[1:]

    args = get_args_parser().parse_args(argv)

    # Commands that manage their own config (e.g. "test") skip standard config loading
    if getattr(args, "standalone_command", False):
        args.run_command(args=args)
        return

    # Evaluate tactus host, config and schema paths
    tactus_host = TactusHost().detect_tactus_host()
    with contextlib.suppress(AttributeError):
        if args.config_data_dir is not None:
            ConfigPaths.add_config_data_dirs(args.config_data_dir)

    with contextlib.suppress(AttributeError):
        if args.schema_dir is not None:
            ConfigPaths.add_schema_dirs(args.schema_dir)

    schema_paths = get_main_config_schema_paths(args.schema)
    config = ParsedConfig.from_file(
        args.config_file,
        json_schema=get_main_config_json_schema(schema_paths),
        host=tactus_host,
    )
    config.metadata["schema_files"] = [str(path) for path in schema_paths]

    with contextlib.suppress(KeyError):
        # Reset default loglevel if specified in the config
        logger.configure(
            handlers=LoggerHandlers(default_level=config["general.loglevel"])
        )

    config = config.copy(
        update={
            "genesis": {
                "command": GeneralConstants.PACKAGE_NAME + " " + " ".join(argv),
                "package": GeneralConstants.PACKAGE_NAME,
                "version": GeneralConstants.VERSION,
                "time": datetime.datetime.now().isoformat(timespec="seconds"),
                "user": os.environ.get("USER"),
            }
        }
    )
    args.run_command(args=args, config=config)


if __name__ == "__main__":
    main()
