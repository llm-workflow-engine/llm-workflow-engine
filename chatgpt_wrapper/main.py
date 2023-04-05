import argparse
import os
import sys

from chatgpt_wrapper.version import __version__
import chatgpt_wrapper.core.constants as constants
from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.backends.browser.chatgpt import ChatGPT
from chatgpt_wrapper.backends.browser.repl import BrowserRepl
from chatgpt_wrapper.backends.openai.repl import ApiRepl

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
        help=f"directory to read config from (default: {dummy_config.config_dir})",
    )
    parser.add_argument(
        "-p",
        "--config-profile",
        action="store",
        help=f"config profile to use (default: {dummy_config.profile})",
    )
    parser.add_argument(
        "-t",
        "--data-dir",
        action="store",
        help=f"directory to read/store data from (default: {dummy_config.data_dir})",
    )
    parser.add_argument(
        "--database",
        action="store",
        help=f"Database to store chat-related data (default: {dummy_config.get('database')})",
    )
    parser.add_argument(
        "-n", "--no-stream", default=True, dest="stream", action="store_false",
        help="disable streaming mode"
    )
    parser.add_argument(
        "-l",
        "--log",
        action="store",
        help="log prompts and responses to the named file",
    )
    parser.add_argument(
        "-e",
        "--debug-log",
        metavar="FILEPATH",
        action="store",
        help="debug logging to FILEPATH",
    )
    parser.add_argument(
        "-b",
        "--browser",
        action="store",
        help="set preferred browser; 'firefox' 'chromium' or 'webkit'",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=['default', 'legacy-paid', 'legacy-free', 'gpt4'],
        action="store",
        help="set preferred model",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="enable debug mode in which the browser window is not hidden",
    )
    args = parser.parse_args()

    config_args = {}
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
    config.set('chat.streaming', args.stream)
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
    if args.model is not None:
        config.set('chat.model', args.model)

    command = None
    if len(args.params) == 1 and args.params[0] in constants.SHELL_ONE_SHOT_COMMANDS:
        command = args.params[0]

    backend = config.get('backend')
    if backend == 'chatgpt-browser':
        if command == 'reinstall':
            print('Reinstalling...')
            temp_backend = ChatGPT(config)
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
    elif backend == 'chatgpt-api':
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


    if len(args.params) > 0 and not command:
        shell.launch_backend(interactive=False)
        shell.default(" ".join(args.params))
        exit(0)
    else:
        shell.launch_backend()

    shell.cmdloop()
    shell.cleanup()

if __name__ == "__main__":
    main()
