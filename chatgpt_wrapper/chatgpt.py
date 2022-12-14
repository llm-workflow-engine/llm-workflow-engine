import argparse
import base64
import cmd
import json
import operator
import platform
import sys
import uuid
from functools import reduce
from time import sleep

# use pyreadline3 instead of readline on windows
is_windows = platform.system() == "Windows"
if is_windows:
    import pyreadline3  # noqa: F401
else:
    import readline

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.markdown import Markdown

console = Console()


class ChatGPT:
    """
    A ChatGPT interface that uses Playwright to run a browser,
    and interacts with that browser to communicate with ChatGPT in
    order to provide an open API to ChatGPT.
    """

    stream_div_id = "chatgpt-wrapper-conversation-stream-data"
    eof_div_id = "chatgpt-wrapper-conversation-stream-data-eof"
    session_div_id = "chatgpt-wrapper-session-data"

    def __init__(self, headless: bool = True, browser = "firefox"):
        self.play = sync_playwright().start()

        try:
            playbrowser = getattr(self.play, browser)
        except Exception:
            print(f"Browser {browser} is invalid, falling back on firefox")
            playbrowser = self.play.firefox

        self.browser = playbrowser.launch_persistent_context(
            user_data_dir="/tmp/playwright",
            headless=headless,
        )
        self.page = self.browser.new_page()
        self._start_browser()
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.session = None

    def _start_browser(self):
        self.page.goto("https://chat.openai.com/")

    def refresh_session(self):
        self.page.evaluate(
            """
        const xhr = new XMLHttpRequest();
        xhr.open('GET', 'https://chat.openai.com/api/auth/session');
        xhr.onload = () => {
          if(xhr.status == 200) {
            var mydiv = document.createElement('DIV');
            mydiv.id = "SESSION_DIV_ID"
            mydiv.innerHTML = xhr.responseText;
            document.body.appendChild(mydiv);
          }
        };
        xhr.send();
        """.replace(
                "SESSION_DIV_ID", self.session_div_id
            )
        )

        while True:
            session_datas = self.page.query_selector_all(f"div#{self.session_div_id}")
            if len(session_datas) > 0:
                break
            sleep(0.2)

        session_data = json.loads(session_datas[0].inner_text())
        self.session = session_data

        self.page.evaluate(f"document.getElementById('{self.session_div_id}').remove()")

    def _cleanup_divs(self):
        self.page.evaluate(f"document.getElementById('{self.stream_div_id}').remove()")
        self.page.evaluate(f"document.getElementById('{self.eof_div_id}').remove()")

    def ask_stream(self, prompt: str):
        if self.session is None:
            self.refresh_session()

        new_message_id = str(uuid.uuid4())

        if "accessToken" not in self.session:
            yield (
                "Your ChatGPT session is not usable.\n"
                "* Run this program with the `install` parameter and log in to ChatGPT.\n"
                "* If you think you are already logged in, try running the `session` command."
            )
            return

        request = {
            "messages": [
                {
                    "id": new_message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [prompt]},
                }
            ],
            "model": "text-davinci-002-render",
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_message_id,
            "action": "next",
        }

        code = (
            """
            const stream_div = document.createElement('DIV');
            stream_div.id = "STREAM_DIV_ID";
            document.body.appendChild(stream_div);
            const xhr = new XMLHttpRequest();
            xhr.open('POST', 'https://chat.openai.com/backend-api/conversation');
            xhr.setRequestHeader('Accept', 'text/event-stream');
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Authorization', 'Bearer BEARER_TOKEN');
            xhr.responseType = 'stream';
            xhr.onreadystatechange = function() {
              var newEvent;
              if(xhr.readyState == 3 || xhr.readyState == 4) {
                const newData = xhr.response.substr(xhr.seenBytes);
                try {
                  const newEvents = newData.split(/\\n\\n/).reverse();
                  newEvents.shift();
                  if(newEvents[0] == "data: [DONE]") {
                    newEvents.shift();
                  }
                  if(newEvents.length > 0) {
                    newEvent = newEvents[0].substring(6);
                    // using XHR for eventstream sucks and occasionally ive seen incomplete
                    // json objects come through  JSON.parse will throw if that happens, and
                    // that should just skip until we get a full response.
                    JSON.parse(newEvent);
                  }
                } catch (err) {
                  console.log(err);
                  return;
                }
                if(newEvent !== undefined) {
                  stream_div.innerHTML = btoa(newEvent);
                  xhr.seenBytes = xhr.responseText.length;
                }
              }
              if(xhr.readyState == 4) {
                const eof_div = document.createElement('DIV');
                eof_div.id = "EOF_DIV_ID";
                document.body.appendChild(eof_div);
              }
            };
            xhr.send(JSON.stringify(REQUEST_JSON));
            """.replace(
                "BEARER_TOKEN", self.session["accessToken"]
            )
            .replace("REQUEST_JSON", json.dumps(request))
            .replace("STREAM_DIV_ID", self.stream_div_id)
            .replace("EOF_DIV_ID", self.eof_div_id)
        )

        self.page.evaluate(code)

        last_event_msg = ""
        while True:
            eof_datas = self.page.query_selector_all(f"div#{self.eof_div_id}")

            conversation_datas = self.page.query_selector_all(
                f"div#{self.stream_div_id}"
            )
            if len(conversation_datas) == 0:
                continue

            full_event_message = None

            try:
                event_raw = base64.b64decode(conversation_datas[0].inner_html())
                if len(event_raw) > 0:
                    event = json.loads(event_raw)
                    if event is not None:
                        self.parent_message_id = event["message"]["id"]
                        self.conversation_id = event["conversation_id"]
                        full_event_message = "\n".join(
                            event["message"]["content"]["parts"]
                        )
            except Exception:
                yield (
                    "Failed to read response from ChatGPT.  Tips:\n"
                    " * Try again.  ChatGPT can be flaky.\n"
                    " * Use the `session` command to refresh your session, and then try again.\n"
                    " * Restart the program in the `install` mode and make sure you are logged in."
                )
                break

            if full_event_message is not None:
                chunk = full_event_message[len(last_event_msg) :]
                last_event_msg = full_event_message
                yield chunk

            # if we saw the eof signal, this was the last event we
            # should process and we are done
            if len(eof_datas) > 0:
                break

            sleep(0.2)

        self._cleanup_divs()

    def ask(self, message: str) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        response = list(self.ask_stream(message))
        return (
            reduce(operator.add, response)
            if len(response) > 0
            else "Unusable response produced by ChatGPT, maybe its unavailable."
        )

    def new_conversation(self):
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None


class GPTShell(cmd.Cmd):
    """
    A `cmd` interpreter that serves as a front end to the ChatGPT class
    """

    # overrides
    intro = "Provide a prompt for ChatGPT, or type help or ? to list commands."
    prompt = "> "

    # our stuff
    prompt_number = 0
    chatgpt = None
    message_map = {}
    stream = False
    logfile = None

    def _set_args(self, args):
        self.stream = args.stream
        if args.log is not None:
            if not self._open_log(args.log):
                sys.exit(0)

    def _set_chatgpt(self, chatgpt):
        self.chatgpt = chatgpt
        self._update_message_map()

    def _set_prompt(self):
        self.prompt = f"{self.prompt_number}> "

    def _update_message_map(self):
        self.prompt_number += 1
        self.message_map[self.prompt_number] = (
            self.chatgpt.conversation_id,
            self.chatgpt.parent_message_id,
        )
        self._set_prompt()

    def _print_markdown(self, output):
        console.print(Markdown(output))
        print("")

    def _write_log(self, prompt, response):
        if self.logfile is not None:
            self.logfile.write(f"{self.prompt_number}> {prompt}\n\n{response}\n\n")
            self._write_log_context()

    def _write_log_context(self):
        if self.logfile is not None:
            self.logfile.write(
                f"## context {self.chatgpt.conversation_id}:{self.chatgpt.parent_message_id}\n"
            )
            self.logfile.flush()

    def emptyline(self):
        """
        override cmd.Cmd.emptyline so it does not repeat
        the last command when you hit enter
        """
        return

    def do_stream(self, _):
        "`stream` toggles between streaming mode (streams the raw response from ChatGPT) and markdown rendering (which cannot stream)."
        self.stream = not self.stream
        self._print_markdown(
            f"* Streaming mode is now {'enabled' if self.stream else 'disabled'}."
        )

    def do_new(self, _):
        "`new` starts a new conversation."
        self.chatgpt.new_conversation()
        self._print_markdown("* New conversation started.")
        self._update_message_map()
        self._write_log_context()

    def do_nav(self, arg):
        "`nav` lets you navigate to a past point in the conversation. Example: `nav 2`"

        try:
            msg_id = int(arg)
        except Exception:
            self._print_markdown("The argument to nav must be an integer.")
            return

        if msg_id == self.prompt_number:
            self._print_markdown("You are already using prompt {msg_id}.")
            return

        if msg_id not in self.message_map:
            self._print_markdown(
                "The argument to `nav` contained an unknown prompt number."
            )
            return

        (
            self.chatgpt.conversation_id,
            self.chatgpt.parent_message_id,
        ) = self.message_map[msg_id]
        self._update_message_map()
        self._write_log_context()
        self._print_markdown(
            f"* Prompt {self.prompt_number} will use the context from prompt {arg}."
        )

    def do_exit(self, _):
        "`exit` closes the program."
        sys.exit(0)

    def default(self, line):

        if self.stream:
            response = ""
            first = True
            for chunk in self.chatgpt.ask_stream(line):
                if first:
                    print("")
                    first = False
                print(chunk, end="")
                sys.stdout.flush()
                response += chunk
            print("\n")
        else:
            response = self.chatgpt.ask(line)
            print("")
            self._print_markdown(response)

        self._write_log(line, response)
        self._update_message_map()

    def do_session(self, _):
        "`session` refreshes your session information.  This can resolve errors under certain scenarios."
        self.chatgpt.refresh_session()
        usable = (
            "The session appears to be usable."
            if "accessToken" in self.chatgpt.session
            else "The session is not usable.  Try `install` mode."
        )
        self._print_markdown(f"* Session information refreshed.  {usable}")

    def do_read(self, _):
        "`read` begins reading multi-line input."
        ctrl_sequence = "^z" if is_windows else "^d"
        self._print_markdown(f"* Reading prompt, hit {ctrl_sequence} when done.")

        if not is_windows:
            readline.set_auto_history(False)

        prompt = ""
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "":
                print("")
            prompt += line + "\n"

        if not is_windows:
            readline.set_auto_history(True)
            readline.add_history(prompt)

        self.default(prompt)

    def do_file(self, arg):
        "`file` sends a prompt read from the named file.  Example: `file myprompt.txt`"
        try:
            fileprompt = open(arg).read()
        except Exception:
            self._print_markdown(f"Failed to read file '{arg}'")
            return
        self.default(fileprompt)

    def _open_log(self, filename) -> bool:
        try:
            self.logfile = open(filename, "a")
        except Exception:
            self._print_markdown(f"Failed to open log file '{filename}'.")
            return False
        return True

    def do_log(self, arg):
        "`log` enables logging to a file.  Example: `log mylog.txt` to enable, or `log` to disable."
        if arg:
            if self._open_log(arg):
                self._print_markdown(f"* Logging enabled, appending to '{arg}'.")
        else:
            self.logfile = None
            self._print_markdown(f"* Logging is now disabled.")

    def do_context(self, arg):
        "`context` lets you load old contexts from the log.  It takes one parameter; a context string from logs."
        try:
            (conversation_id, parent_message_id) = arg.split(":")
            assert conversation_id == "None" or len(conversation_id) == 36
            assert len(parent_message_id) == 36
        except:
            self._print_markdown("Invalid parameter to `context`.")
            return
        self._print_markdown(f"* Loaded specified context.")
        self.chatgpt.conversation_id = (
            conversation_id if conversation_id != "None" else None
        )
        self.chatgpt.parent_message_id = parent_message_id
        self._update_message_map()
        self._write_log_context()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "params",
        nargs="*",
        help="Use 'install' for install mode, or provide a prompt for ChatGPT.",
    )
    parser.add_argument(
        "-s", "--stream", action="store_true", help="enable streaming mode"
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
            "through all the dialogs, etc. Once that is acheived, exit and restart\n"
            "this program without the 'install' parameter.\n"
        )

    extra_kwargs = {} if args.browser is None else {"browser": args.browser}
    chatgpt = ChatGPT(headless=not install_mode, **extra_kwargs)

    shell = GPTShell()
    shell._set_chatgpt(chatgpt)
    shell._set_args(args)

    if len(args.params) > 0 and not install_mode:
        shell.default(" ".join(args.params))
        return

    shell.cmdloop()


if __name__ == "__main__":
    main()
