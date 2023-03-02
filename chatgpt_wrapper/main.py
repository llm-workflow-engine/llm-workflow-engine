import argparse
import sys
import asyncio

from chatgpt_wrapper.chatgpt import AsyncChatGPT
from chatgpt_wrapper.gpt_shell import GPTShell
from chatgpt_wrapper.version import __version__

def main():
    asyncio.run(async_main())

async def async_main():

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
    install_mode = len(args.params) == 1 and args.params[0] == "install"

    if install_mode:
        print(
            "Install mode: Log in to ChatGPT in the browser that pops up, and click\n"
            "through all the dialogs, etc. Once that is achieved, exit and restart\n"
            "this program without the 'install' parameter.\n"
        )

    extra_kwargs = {}
    if args.browser is not None:
        extra_kwargs["browser"] = args.browser
    if args.model is not None:
        extra_kwargs["model"] = args.model
    if args.debug_log is not None:
        extra_kwargs["debug_log"] = args.debug_log
    chatgpt = await AsyncChatGPT().create(headless=not (install_mode or args.debug), timeout=90, **extra_kwargs)

    shell = GPTShell()
    shell._set_chatgpt(chatgpt)
    await shell._set_args(args)

    if len(args.params) > 0 and not install_mode:
        await shell.default(" ".join(args.params))
        return

    await shell.cmdloop()
    await chatgpt.cleanup()

if __name__ == "__main__":
    main()
