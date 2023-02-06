import argparse
import sys

from chatgpt import ChatGPT
from gpt_shell import GPTShell

VERSION = "0.3.13"


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"{sys.argv[0]} version {VERSION}",
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
        "-b",
        "--browser",
        action="store",
        help="set preferred browser; 'firefox' 'chromium' or 'webkit'",
    )
    args = parser.parse_args()
    install_mode = len(args.params) == 1 and args.params[0] == "install"

    if install_mode:
        print(
            "Install mode: Log in to ChatGPT in the browser that pops up, and click\n"
            "through all the dialogs, etc. Once that is achieved, exit and restart\n"
            "this program without the 'install' parameter.\n"
        )

    extra_kwargs = {} if args.browser is None else {"browser": args.browser}
    chatgpt = ChatGPT(headless=not install_mode, timeout=90, **extra_kwargs)

    shell = GPTShell()
    shell._set_chatgpt(chatgpt)
    shell._set_args(args)

    if len(args.params) > 0 and not install_mode:
        shell.default(" ".join(args.params))
        return

    shell.cmdloop()


if __name__ == "__main__":
    main()
