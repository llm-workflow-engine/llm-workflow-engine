import cmd
import base64
import json
import os
import re
import readline
import sys
import tempfile
import time
import uuid
from time import sleep

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.markdown import Markdown

console = Console()


class ChatGPT:
    """
    A ChatGPT interface that uses Playwright to run a browser,
    and interacts with that browser to communicate with ChatGPT in
    order to provide a command line interface to ChatGPT.
    """

    def __init__(self, headless: bool = True):
        self.play = sync_playwright().start()
        self.browser = self.play.firefox.launch_persistent_context(
            user_data_dir=f"/tmp/playwright",
            headless=headless,
        )
        self.page = self.browser.new_page()
        self._start_browser()
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None

    def _start_browser(self):
        self.page.goto("https://chat.openai.com/")
        self.refresh_session()

    def refresh_session(self):
        self.page.evaluate(
            """
        const xhr = new XMLHttpRequest();
        xhr.open('GET', 'https://chat.openai.com/api/auth/session');
        xhr.onload = () => {
          if(xhr.status == 200) {
            var mydiv = document.createElement('DIV');
            mydiv.id = "chatgpt-wrapper-session-data"
            mydiv.innerHTML = xhr.responseText;
            document.body.appendChild(mydiv);
          }
        };
        xhr.send();
        """
        )

        while True:
            session_datas = self.page.query_selector_all(
                "div#chatgpt-wrapper-session-data"
            )
            if len(session_datas) > 0:
                break
            sleep(0.2)

        session_data = json.loads(session_datas[0].inner_text())
        self.session = session_data

        self.page.evaluate(
            "document.getElementById('chatgpt-wrapper-session-data').remove()"
        )

    def _send_message(self, message: str):
        new_message_id = str(uuid.uuid4())

        if not "accessToken" in self.session:
            return (
                "Your ChatGPT session is not usable.\n"
                "* Run this program with the `install` parameter and log in to ChatGPT."
            )

        request = {
            "messages": [
                {
                    "id": new_message_id,
                    "role": "user",
                    "content": {"content_type": "text", "parts": [message]},
                }
            ],
            "model": "text-davinci-002-render",
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_message_id,
            "action": "next",
        }

        code = """
            const xhr = new XMLHttpRequest();
            xhr.open('POST', 'https://chat.openai.com/backend-api/conversation');
            xhr.setRequestHeader('Accept', 'text/event-stream');
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Authorization', 'Bearer BEARER_TOKEN');
            xhr.onload = () => {
              var mydiv = document.createElement('DIV');
              mydiv.id = "chatgpt-wrapper-conversation-data";
              if(xhr.status == 200) {
                mydiv.innerHTML = btoa(xhr.responseText);
              } else {
                mydiv.innerHTML = "";
              }
              document.body.appendChild(mydiv);
            };

            xhr.send(JSON.stringify(REQUEST_JSON));
            """.replace(
            "BEARER_TOKEN", self.session["accessToken"]
        ).replace(
            "REQUEST_JSON", json.dumps(request)
        )

        self.page.evaluate(code)

        while True:
            conversation_datas = self.page.query_selector_all(
                "div#chatgpt-wrapper-conversation-data"
            )
            if len(conversation_datas) > 0:
                break
            sleep(0.2)

        try:
            # the xhr response is an http event stream of json objects.
            # the div contains that entire response, base64 encoded to
            # avoid html entities issues.  the complete response is always
            # the third from last event.  the json itself always begins at
            # character 6.
            response = json.loads(
                base64.b64decode(conversation_datas[0].inner_html()).split(b"\n\n")[-3][6:]
            )
        except:
            return (
                "Failed to read response from ChatGPT.  Tips:\n"
                " * Try again.  ChatGPT can be flaky.\n"
                " * Use the `session` command to refresh your session, and then try again.\n"
                " * Restart the program in the `install` mode and make sure you are logged in."
            )

        finally:
            self.page.evaluate(
                "document.getElementById('chatgpt-wrapper-conversation-data').remove()"
            )

        self.parent_message_id = new_message_id
        self.conversation_id = response["conversation_id"]

        return "\n".join(response["message"]["content"]["parts"])

    def ask(self, message: str) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        return self._send_message(message)


class GPTShell(cmd.Cmd):
    intro = "Provide a prompt for ChatGPT, or type help or ? to list commands."
    prompt = "> "

    chatgpt = None

    def _print_output(self, output):
        console.print(Markdown(output))
        print("")

    def do_clear(self, _):
        "`clear` starts a new conversation, chatgpt will lose all conversational context."
        self.chatgpt.parent_message_id = str(uuid.uuid4())
        self.chatgpt.conversation_id = None
        self._print_output('* Conversation cleared')

    def do_exit(self, _):
        "`exit` closes the program."
        sys.exit(0)

    def default(self, line):
        response = self.chatgpt.ask(line)
        print("")
        self._print_output(response)

    def do_session(self, _):
        "`session` refreshes your session information"
        self.chatgpt.refresh_session()
        self._print_output('* Session refreshed')

def main():

    install_mode = len(sys.argv) > 1 and (sys.argv[1] == "install")
    if install_mode:
        print(
            "Install mode: Log in to ChatGPT in the browser that pops up, and click\n"
            "through all the dialogs, etc. Once that is acheived, exit and restart\n"
            "this program without the 'install' parameter.\n"
        )

    chatgpt = ChatGPT(headless=not install_mode)

    if len(sys.argv) > 1 and not install_mode:
        response = chatgpt.ask(" ".join(sys.argv[1:]))
        console.print(Markdown(response))
        return

    shell = GPTShell()
    shell.chatgpt = chatgpt
    shell.cmdloop()


if __name__ == "__main__":
    main()
