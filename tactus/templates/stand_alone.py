"""NoSchedulerTemplate."""

import json
import os

from tactus.config_parser import ConfigPaths, GeneralConstants, ParsedConfig
from tactus.config_schema import (
    get_main_config_json_schema,
    get_main_config_schema_paths,
)
from tactus.derived_variables import derived_variables, set_times
from tactus.eps.eps_setup import get_member_config
from tactus.host_actions import TactusHost
from tactus.logs import logger  # Use tactus's own configs for logger
from tactus.submission import ProcessorLayout, TaskSettings
from tactus.tasks.discover_task import get_task

logger.enable("tactus")


def default_main(task: str, config_file: str, tactus_home: str, schema_paths=None):
    """Execute default main.

    Args:
        task (str): Task name
        config_file (str): Config file
        tactus_home(str): tactus home path
        schema_paths (list[Path] | None): Schema files used to validate the config.
    """
    schema_paths = get_main_config_schema_paths(schema_paths)
    ConfigPaths.add_schema_paths(schema_paths)
    tactus_host = TactusHost().detect_tactus_host()
    logger.info("Read config from {}", config_file)
    config = ParsedConfig.from_file(
        config_file,
        json_schema=get_main_config_json_schema(schema_paths),
        host=tactus_host,
    )
    config.metadata["schema_files"] = [str(path) for path in schema_paths]
    # Get eps member specific config if a member is specified
    member_info = ""
    if config.get("task.args.use_member_stand_alone", True):
        try:
            member = int(config["general.member"])
        except (KeyError, TypeError, ValueError):
            logger.debug("MEMBER is not an integer, skipping eps setup for task {}", task)
        else:
            # Update config based on member
            logger.info("Setup EPS")
            config = get_member_config(config, member=member)
            member_info = f" for member {member}"

    config = config.copy(update=set_times(config))
    config = config.copy(update={"platform": {"tactus_home": tactus_home}})

    task_settings = TaskSettings(config).get_task_settings(task)
    processor_layout = ProcessorLayout(task_settings)
    if config.get("domain.nbzonl") is not None:
        update = derived_variables(config, processor_layout=processor_layout)
        config = config.copy(update=update)

    logger.info("Running {}{}", task, member_info)
    get_task(task, config).run()
    logger.info("Finished {}{}", task, member_info)


if __name__ == "__main__":
    logger.info("Running {} v{}", GeneralConstants.PACKAGE_NAME, GeneralConstants.VERSION)
    default_main(
        task=os.environ["STAND_ALONE_TASK_NAME"],
        config_file=os.environ["STAND_ALONE_TASK_CONFIG"],
        tactus_home=os.environ["STAND_ALONE_TACTUS_HOME"],
        schema_paths=json.loads(os.environ.get("STAND_ALONE_SCHEMAS", "null")),
    )
