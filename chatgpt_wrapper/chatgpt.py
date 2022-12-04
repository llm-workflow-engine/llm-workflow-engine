
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

    def __init__(self, headless: bool = True, timeout: int = 60):
        if not headless:
            print("\n Please login to OpenAI Chat and accept the cookies box then restart the script")
        self.timeout = timeout
        self.last_msg = None
        self.play = sync_playwright().start()
        self.browser = self.play.firefox.launch_persistent_context(
            user_data_dir=f"/tmp/playwright",
            headless=headless,
        )
        self.page = self.browser.new_page()
        self._start_browser()


    def _start_browser(self):
        self.page.goto("https://chat.openai.com/")
        if not self._is_logged_in():
            print("Please log in to OpenAI Chat and accept the cookies box")
            print("Press enter when you're done")
            input()

    def _get_input_box(self):
        """Get the child textarea of `PromptTextarea__TextareaWrapper`"""
        return self.page.query_selector("textarea")

    def _is_logged_in(self):
        # See if we have a textarea with data-id="root"
        return self._get_input_box() is not None

    def _parse_last_elem(self) -> str:
        """Get the latest message"""
        try:
            msg = self.page.query_selector_all("div[class*='ConversationItem__Message']")[-1].inner_text()
        except:
            msg = ""
        msg = re.sub('\u200b', '', msg)
        return msg

    def _send_message(self, message: str):
        # Send the message
        box = self._get_input_box()
        box.click()
        box.fill(message)
        self.last_msg = self._parse_last_elem()
        box.press("Enter")

    def _get_last_message(self) -> str:
        """Get the latest message"""
        page_elements = self.page.query_selector_all("div[class*='ConversationItem__Message']")
        if self._parse_last_elem() != self.last_msg:
            while True:
                msg = self._parse_last_elem()
                sleep(1)
                if msg == self._parse_last_elem():
                    break
            return msg
        return None

    def ask(self, message: str) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        self._send_message(message)

        timeout = time.time() + self.timeout
        while True:
            response = self._get_last_message()
            if response:
                break
            if time.time() > timeout:
                raise TimeoutError("Timed out while waiting for the response")

        response = self._get_last_message()
        return response


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            chatbot = ChatGPT(headless=False)
            sleep(100)
        else:
            chatbot = ChatGPT()
            # Print the output of chatbot.ask and exit the script
            print(chatbot.ask(" ".join(sys.argv[1:])))
            sys.exit()
    chatbot = ChatGPT()
    while True:
        inp = input("You: ")
        if inp == "exit":
            sys.exit(0)
        response = chatbot.ask(inp)
        print("\nChatGPT: " + response + "\n")


if __name__ == "__main__":
    main()
