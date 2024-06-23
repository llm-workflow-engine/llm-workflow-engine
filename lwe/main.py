import argparse
import os
import sys

from lwe.version import __version__
import lwe.core.constants as constants
from lwe.core.config import Config
from lwe.core import util
from lwe.backends.api.repl import ApiRepl

USER_DIRECTORIES = [
    "templates",
    "presets",
    "plugins",
    "workflows",
    "tools",
]


def main():
    dummy_config = Config()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"{sys.argv[0]} version {__version__}",
        help="Print version and exit.",
    )
    parser.add_argument(
        "params",
        nargs="*",
        help="Use 'config' to see current configuration, or provide a prompt.",
    )
    parser.add_argument(
        "-c",
        "--config-dir",
        action="store",
        help=f"Directory to read config from (default: {dummy_config.config_dir})",
    )
    parser.add_argument(
        "-p",
        "--config-profile",
        action="store",
        help=f"Config profile to use (default: {dummy_config.profile})",
    )
    parser.add_argument(
        "-t",
        "--data-dir",
        action="store",
        help=f"Directory to read/store data from (default: {dummy_config.data_dir})",
    )
    parser.add_argument(
        "-r",
        "--preset",
        metavar="PRESET",
        action="store",
        help="Preset to use on startup",
    )
    parser.add_argument(
        "-s",
        "--system-message",
        metavar="ALIAS_NAME",
        action="store",
        help="Alias name of the system message to use on startup",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=argparse.FileType("r"),
        default=None,
        const=sys.stdin,
        nargs="?",
        help="Input file (default: read from stdin)",
    )
    parser.add_argument(
        "-l",
        "--log",
        action="store",
        help="Log prompts and responses to the named file",
    )
    parser.add_argument(
        "-n",
        "--no-stream",
        default=True,
        dest="stream",
        action="store_false",
        help="Disable streaming mode",
    )
    parser.add_argument(
        "--database",
        action="store",
        help=f"Database to store chat-related data (default: {dummy_config.get('database')})",
    )
    parser.add_argument(
        "-w",
        "--workflow",
        action="store",
        help="Workflow to run",
    )
    parser.add_argument(
        "--workflow-args",
        default="",
        action="store",
        help="Arguments to pass to the workflow",
    )
    parser.add_argument(
        "--cache-dir",
        metavar="PATH",
        action="append",
        help="Cache directory (can be specified multiple times)",
    )
    for directory in USER_DIRECTORIES:
        parser.add_argument(
            f"--{directory}-dir",
            metavar="PATH",
            action="append",
            help=f"User {directory} directory (can be specified multiple times)",
        )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "-e",
        "--debug-log",
        metavar="FILEPATH",
        action="store",
        help="Debug logging to FILEPATH",
    )

    args = parser.parse_args()

    config_args = {
        "args": args,
    }
    config_dir = args.config_dir or os.environ.get("LWE_CONFIG_DIR", None)
    config_profile = args.config_profile or os.environ.get("LWE_CONFIG_PROFILE", None)
    data_dir = args.data_dir or os.environ.get("LWE_DATA_DIR", None)
    if config_dir:
        config_args["config_dir"] = config_dir
    if config_profile:
        config_args["profile"] = config_profile
    if data_dir:
        config_args["data_dir"] = data_dir
    config = Config(**config_args)
    config.load_from_file()

    if args.database is not None:
        config.set("database", args.database)
    config.set("shell.streaming", args.stream)
    if args.log is not None:
        config.set("chat.log.enabled", True)
        config.set("chat.log.filepath", args.log)
    if args.debug_log is not None:
        config.set("debug.log.enabled", True)
        config.set("debug.log.filepath", args.debug_log)
    if args.debug:
        config.set("log.console.level", "debug")
        config.set("debug.log.enabled", True)
        config.set("debug.log.level", "debug")
    if args.preset is not None:
        config.set("model.default_preset", args.preset)
    if args.cache_dir is not None:
        config.set("directories.cache", args.cache_dir)
    for directory in USER_DIRECTORIES:
        if getattr(args, f"{directory}_dir") is not None:
            config.set(f"directories.{directory}", getattr(args, f"{directory}_dir"))
    if args.system_message is not None:
        config.set("model.default_system_message", args.system_message)

    command = None
    if len(args.params) > 0 and args.params[0] in constants.SHELL_ONE_SHOT_COMMANDS:
        command = args.params[0]

    backend = config.get("backend")
    if backend != "api":
        config.set("backend", "api")
        util.print_status_message(False, f"Using legacy backend setting: {backend}")
        util.print_status_message(
            False,
            "To dismiss this warning, edit the 'backend' setting in your configuration to 'api', or remove the setting from your configuration.",
        )
    shell = ApiRepl(config)
    shell.setup()

    if command == "config":
        config_args = " ".join(args.params[1:]) if len(args.params) > 1 else ""
        shell.command_config(config_args)
        exit(0)

    shell_prompt = []
    if len(args.params) > 0:
        args_string = " ".join(args.params)
        shell.log.debug(f"Processed extra arguments: {args_string}")
        shell_prompt.append(args_string)
    if args.input_file is not None:
        shell.log.debug(f"Processing input file: {args.input_file}")
        file_string = args.input_file.read()
        shell_prompt.append(file_string)
        shell.log.debug(f"Processed input file contents: {file_string}")

    if shell_prompt and not command:
        shell.log.debug("Launching one-shot prompt")
        shell.launch_backend(interactive=False)
        shell.default("\n\n".join(shell_prompt))
        exit(0)
    else:
        if args.workflow is not None:
            success, result, user_message = shell.backend.workflow_manager.run(
                args.workflow, args.workflow_args
            )
            util.print_status_message(success, user_message)
            exit(0)
        else:
            shell.launch_backend()

    shell.cmdloop()
    shell.cleanup()


if __name__ == "__main__":
    main()
