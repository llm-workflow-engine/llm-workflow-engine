import uuid
import json
import re
import os
import sys
import time
import tempfile
from time import sleep
import tempfile
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

        code = (
            """
            const xhr = new XMLHttpRequest();
            xhr.open('POST', 'https://chat.openai.com/backend-api/conversation');
            xhr.setRequestHeader('Accept', 'text/event-stream');
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Authorization', 'Bearer BEARER_TOKEN');
            xhr.onload = () => {
              if(xhr.status == 200) {
                var mydiv = document.createElement('DIV');
                mydiv.id = "chatgpt-wrapper-conversation-data";
                mydiv.innerHTML = xhr.responseText;
                document.body.appendChild(mydiv);
              }
            };

            xhr.send(JSON.stringify(REQUEST_JSON));
            """
            .replace("BEARER_TOKEN", self.session["accessToken"])
            .replace("REQUEST_JSON", json.dumps(request))
        )

        self.page.evaluate(code)

        while True:
            conversation_datas = self.page.query_selector_all(
                "div#chatgpt-wrapper-conversation-data"
            )
            if len(conversation_datas) > 0:
                break
            sleep(0.2)

        self.parent_message_id = new_message_id

        response = json.loads(conversation_datas[0].inner_html().split("\n\n")[-3][6:])
        self.page.evaluate(
            "document.getElementById('chatgpt-wrapper-conversation-data').remove()"
        )

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


def main():
    install_mode = len(sys.argv) > 1 and (sys.argv[1] == "install")

    if install_mode:
        print(
            "Log in to ChatGPT in the browser that pops up, and click through all the dialogs, etc.  Once that is acheived, ctrl-c and restart this program without the 'install' parameter."
        )

    chatgpt = ChatGPT(headless=not install_mode)

    while True:

        lines = []
        while True:
            line = input("> ")
            if line:
                lines.append(line)
            else:
                break

        inp = "\n".join(lines).strip()

        if inp == "exit":
            sys.exit(0)
        response = chatgpt.ask(inp)
        print("\n")
        console.print(Markdown(response))
        print("\n")


if __name__ == "__main__":
    main()
