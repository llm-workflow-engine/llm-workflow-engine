
import logging
import re
import os
import sys
import time
import tempfile
from time import sleep

from colorama import Fore, init
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)


class ChatGPT:
    """
    An ChatGPT chatbot that uses Playwright to simulate a Chrome browser.
    The chatbot can be used to send messages to OpenAI and receive responses.
    First time used, the user must log in to OpenAI Chat and accept the cookies box.
    Developed with the help of chatgpt :)
    """

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.last_msg = None
        self.play = sync_playwright().start()
        self.browser = self.play.chromium.launch_persistent_context(
            user_data_dir=f"{tempfile.gettempdir()}{os.path.sep}playwright",
            headless=True,
        )
        self.page = self.browser.new_page()
        self.__start_browser()

    def __start_browser(self):
        self.page.goto("https://chat.openai.com/")
        if not self.__is_logged_in():
            init()  # Enable ANSI escape sequences
            print(Fore.YELLOW + "Please log in to OpenAI Chat and accept the cookies box")
            print(Fore.YELLOW + "Press enter when you're done")
            input()
        print(Fore.BLUE + "Server started" + "\n")

    def __get_input_box(self):
        """Get the child textarea of `PromptTextarea__TextareaWrapper`"""
        return self.page.query_selector("textarea")

    def __is_logged_in(self):
        # See if we have a textarea with data-id="root"
        return self.__get_input_box() is not None

    def __parse_last_elem(self) -> str:
        """Get the latest message"""
        try:
            msg = self.page.query_selector_all("div[class*='ConversationItem__Message']")[-1].inner_text()
        except:
            msg = ""
        msg = re.sub('\u200b', '', msg)
        return msg

    def __send_message(self, message: str):
        # Send the message
        box = self.__get_input_box()
        box.click()
        box.fill(message)
        self.last_msg = self.__parse_last_elem()
        box.press("Enter")

    def __get_last_message(self) -> str:
        """Get the latest message"""
        page_elements = self.page.query_selector_all("div[class*='ConversationItem__Message']")
        if self.__parse_last_elem() != self.last_msg:
            while True:
                msg = self.__parse_last_elem()
                sleep(1)
                if msg == self.__parse_last_elem():
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
        # logging.info("Sending message: %s", message)
        self.__send_message(message)

        timeout = time.time() + self.timeout
        while True:
            response = self.__get_last_message()
            if response:
                break
            if time.time() > timeout:
                raise TimeoutError("Timed out while waiting for the response")

        response = self.__get_last_message()
        # logging.info("Response: %s", response)
        return response


def main():
    chatbot = ChatGPT()
    while True:
        inp = input(Fore.YELLOW + "You: ")
        if inp == "exit":
            sys.exit(0)
        response = chatbot.ask(inp)
        print(Fore.GREEN + "\nChatGPT: " + response + "\n")


if __name__ == "__main__":
    main()
