import argparse
import sys
import asyncio

from chatgpt_wrapper.chatgpt import AsyncChatGPT
from chatgpt_wrapper.gpt_shell import GPTShell
from chatgpt_wrapper.version import __version__
from chatgpt_wrapper.config import Config

def main():
    asyncio.run(async_main())

async def async_main():

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
        help="Use 'install' for install mode, or provide a prompt for ChatGPT.",
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
        choices=['default', 'legacy-paid', 'legacy-free'],
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

    config_args = {
        'config_dir': args.config_dir,
        'data_dir': args.data_dir,
    }
    if args.config_profile:
        config_args['profile'] = args.config_profile
    config = Config(**config_args)
    config.load_from_file()

    install_mode = len(args.params) == 1 and args.params[0] == "install"
    if install_mode:
        print(
            "Install mode: Log in to ChatGPT in the browser that pops up, and click\n"
            "through all the dialogs, etc. Once that is achieved, exit and restart\n"
            "this program without the 'install' parameter.\n"
        )
        config.set('browser.debug', True)

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
    if args.model is not None:
        config.set('chat.model', args.model)

    chatgpt = await AsyncChatGPT(config).create(timeout=90)

    shell = GPTShell(config)
    shell._set_chatgpt(chatgpt)
    await shell._set_args()

    if len(args.params) > 0 and not install_mode:
        await shell.default(" ".join(args.params))
        return

    await shell.cmdloop()
    await chatgpt.cleanup()

if __name__ == "__main__":
    main()
