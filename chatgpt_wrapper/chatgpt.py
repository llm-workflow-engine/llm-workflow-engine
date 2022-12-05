import uuid
import json
import logging
import re
import os
import sys
import time
import tempfile
from time import sleep
import tempfile
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)


class ChatGPT:
    """
    An ChatGPT chatbot that uses Playwright to simulate a Chrome browser.
    The chatbot can be used to send messages to OpenAI and receive responses.
    First time used, the user must log in to OpenAI Chat and accept the cookies box.
    Developed with the help of chatgpt :)
    """

    def __init__(self, headless: bool = True, timeout: int = 600):
        self.timeout = timeout
        self.last_msg = None
        self.play = sync_playwright().start()
        self.browser = self.play.firefox.launch_persistent_context(
            user_data_dir=f"/tmp/playwright",
            headless=headless,
        )
        self.page = self.browser.new_page()
        self._start_browser()
        self.parent_message_id = "00007cb2-5d13-4333-a696-cabb7b0303b2"
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

        session_data = json.loads(session_datas[0].inner_text())
        self.session = session_data

        self.page.evaluate(
            "document.getElementById('chatgpt-wrapper-session-data').remove()"
        )

    def _send_message(self, message: str):

        new_message_id = str(uuid.uuid4())
        code = """
            const xhr = new XMLHttpRequest();
            xhr.open('POST', 'https://chat.openai.com/backend-api/conversation');
            xhr.setRequestHeader('accept', 'text/event-stream');
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
            """.replace(
            "BEARER_TOKEN", self.session["accessToken"]
        ).replace(
            "REQUEST_JSON",
            json.dumps(
                {
                    "messages": [
                        {
                            "id": new_message_id,
                            "role": "user",
                            "content": {"content_type": "text", "parts": [message]},
                        }
                    ],
                    "model": "text-davinci-002-render",
                    "parent_message_id": self.parent_message_id,
                    "conversation_id": self.conversation_id,
                    "action": "next",
                }
            ),
        )

        self.page.evaluate(code)

        while True:
            conversation_datas = self.page.query_selector_all(
                "div#chatgpt-wrapper-conversation-data"
            )
            if len(conversation_datas) > 0:
                break

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

    chatbot = ChatGPT(headless=not install_mode)
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
        response = chatbot.ask(inp)
        print("\n" + response + "\n")


if __name__ == "__main__":
    main()
