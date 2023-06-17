import argparse
import os
import sys

from lwe.version import __version__
import lwe.core.constants as constants
from lwe.core.config import Config
from lwe.core import util
from lwe.backends.browser.backend import BrowserBackend
from lwe.backends.browser.repl import BrowserRepl
from lwe.backends.api.repl import ApiRepl

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
        help="Use 'install' for install mode, 'config' to see current configuration, or provide a prompt.",
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
        help=f"Donfig profile to use (default: {dummy_config.profile})",
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
        type=argparse.FileType('r'),
        default=None,
        const=sys.stdin,
        nargs='?',
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
        "-b",
        "--browser",
        action="store",
        help="Set preferred browser; 'firefox' 'chromium' or 'webkit'",
    )
    parser.add_argument(
        "--database",
        action="store",
        help=f"Database to store chat-related data (default: {dummy_config.get('database')})",
    )
    user_directories = [
        'template',
        'preset',
        'plugin',
        'workflow',
        'function',
    ]
    for directory in user_directories:
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
        help="Enable debug mode in which the browser window is not hidden",
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
        'args': args,
    }
    config_dir = args.config_dir or os.environ.get('CHATGPT_WRAPPER_CONFIG_DIR', None)
    config_profile = args.config_profile or os.environ.get('CHATGPT_WRAPPER_CONFIG_PROFILE', None)
    data_dir = args.data_dir or os.environ.get('CHATGPT_WRAPPER_DATA_DIR', None)
    if config_dir:
        config_args['config_dir'] = config_dir
    if config_profile:
        config_args['profile'] = config_profile
    if data_dir:
        config_args['data_dir'] = data_dir
    config = Config(**config_args)
    config.load_from_file()

    if args.database is not None:
        config.set('database', args.database)
    config.set('model.streaming', args.stream)
    if args.log is not None:
        config.set('chat.log.enabled', True)
        config.set('chat.log.filepath', args.log)
    if args.debug_log is not None:
        config.set('debug.log.enabled', True)
        config.set('debug.log.filepath', args.debug_log)
    if args.browser is not None:
        config.set('browser.provider', args.browser)
    if args.debug:
        config.set('browser.debug', True)
        config.set('log.console.level', 'debug')
        config.set('debug.log.enabled', True)
        config.set('debug.log.level', 'debug')
    if args.preset is not None:
        config.set('model.default_preset', args.preset)
    if args.system_message is not None:
        config.set('model.default_system_message', args.system_message)

    command = None
    if len(args.params) == 1 and args.params[0] in constants.SHELL_ONE_SHOT_COMMANDS:
        command = args.params[0]

    backend = config.get('backend')
    # TODO: Remove this deprecation warning later.
    def backend_deprecation_warning(old, new):
        util.print_status_message(False, f"WARNING: backend '{old}' has been renamed to '{new}', and support for the old name will be removed in a future release. Please update your config file to use '{new}' for the 'backend:' setting.")
    if backend == 'chatgpt-browser':
        backend_deprecation_warning('chatgpt-browser', 'browser')
    if backend == 'chatgpt-api':
        backend_deprecation_warning('chatgpt-api', 'api')
    if backend == 'browser' or backend == 'chatgpt-browser':
        if command == 'reinstall':
            print('Reinstalling...')
            temp_backend = BrowserBackend(config)
            temp_backend.destroy_primary_profile()
            del temp_backend
        if command in ['install', 'reinstall']:
            print(
                "\n"
                "Install mode: Log in to ChatGPT in the browser that pops up, and click\n"
                "through all the dialogs, etc. Once that is achieved, exit and restart\n"
                "this program without the 'install' parameter.\n"
            )
            config.set('browser.debug', True)
        shell = BrowserRepl(config)
    elif backend == 'api' or backend == 'chatgpt-api':
        if command in ['install', 'reinstall']:
            print(
                "\n"
                "Install mode: The API backend is already configured.\n"
            )
        shell = ApiRepl(config)
    else:
        raise RuntimeError(f"Unknown backend: {backend}")
    shell.setup()

    if command == 'config':
        shell.do_config("")
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
        shell.launch_backend()

    shell.cmdloop()
    shell.cleanup()

if __name__ == "__main__":
    main()
