"""NoSchedulerTemplate."""

import json
import os

from tactus import GeneralConstants
from tactus.config_parser import ParsedConfig
from tactus.config_paths import ConfigPaths
from tactus.derived_variables import derived_variables, set_times
from tactus.eps.eps_setup import get_member_config
from tactus.host_actions import TactusHost
from tactus.logs import logger  # Use tactus's own configs for logger
from tactus.submission import ProcessorLayout, TaskSettings
from tactus.tasks.discover_task import get_task

logger.enable("tactus")


def default_main(
    task: str,
    config_file: str,
    tactus_home: str,
    schema_paths=None,
    schema_dirs=None,
):
    """Execute default main.

    Args:
        task (str): Task name
        config_file (str): Config file
        tactus_home(str): tactus home path
        schema_paths (list[Path] | None): Schema files used to validate the config.
        schema_dirs (list[str] | None): Directories used to find schema files.
    """
    ConfigPaths.add_schema_dirs(schema_dirs or [])
    tactus_host = TactusHost().detect_tactus_host()
    logger.info("Read config from {}", config_file)
    config = ParsedConfig.from_file(
        config_file,
        json_schema=schema_paths,
        host=tactus_host,
    )
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
        schema_dirs=json.loads(os.environ.get("STAND_ALONE_SCHEMA_DIRS", "null")),
    )
