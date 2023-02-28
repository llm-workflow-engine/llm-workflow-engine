import logging
import uuid
import re
import time
import json
from json import JSONDecodeError
import shutil
from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import Playwright
from playwright._impl._api_structures import ProxySettings
from typing import Optional
from .log import LogCapability


class Browser(LogCapability):
    """A browser context used by ChatGPT

    This class manages the browser, the page as well as session.
    """
    # A single play can launch many browsers
    play=sync_playwright().start()
    def __init__(self,headless: bool = True, browser="firefox",proxy: Optional[ProxySettings] = None,debug_log=None):
        super().__init__(debug_log=debug_log)
        if not hasattr(self.play,browser):
            self.log.error("Browser %s is invalid, falling back on firefox. ",browser)
            browser='firefox'
        playbrowser=getattr(self.play,browser)

        try:
            self.browser=playbrowser.launch_persistent_context(
                user_data_dir="/tmp/playwright",
                headless=headless,
                proxy=proxy
            )
        except Exception:
            self.user_data_dir=f"/tmp/{str(uuid.uuid4())}"
            shutil.copytree("/tmp/playwright", self.user_data_dir)
            self.browser = playbrowser.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                proxy=proxy,
            )

        self.page=self.browser.new_page()
        self.session={}

    def goto_chatgpt(self):
        self.page.goto("https://chat.openai.com")

    def refresh_session(self,timeout=15):
        """Refresh session, by redirecting the *page* to /api/auth/session rather than a simple xhr request.

        In this way, we can pass the browser check.

        Args:
            timeout (int, optional): Timeout waiting for the refresh in seconds. Defaults to 10.
        """
        self.log.info("Refreshing session...")
        self.page.goto("https://chat.openai.com/api/auth/session")
        try:
            self.page.wait_for_url("/api/auth/session",timeout=timeout*1000)
        except Exception:
            self.log.error("Timed out refreshing session. Page is now at %s. Calling goto_chatgpt()...")
            self.goto_chatgpt()
        try:
            while "Please stand by, while we are checking your browser..." in self.page.content():
                time.sleep(1)
            contents=self.page.content()
            """
            By GETting /api/auth/session, the server would ultimately return a raw json file.
            However, as this is a browser, it will add something to it, like <body> or so, like this:

            <html><head><link rel="stylesheet" href="resource://content-accessible/plaintext.css"></head><body><pre>{xxx:"xxx",{},accessToken="sdjlsfdkjnsldkjfslawefkwnlsdw"}
            </pre></body></html>

            The following code tries to extract the json part from the page, by simply finding the first `{` and the last `}`.
            """
            found_json=re.search('{.*}',contents)
            if found_json==None:
                raise JSONDecodeError("Cannot find JSON in /api/auth/session 's response",contents,0)
            contents=contents[found_json.start():found_json.end()]
            self.log.debug("Refreshing session received: %s",contents)
            self.session=json.loads(contents)
            self.log.info("Succeessfully refreshed session. ")
        except json.JSONDecodeError:
            self.log.error("Failed to decode session key. Maybe Access denied? ")

        # Now the browser should be at /api/auth/session
        # Go back to the chat page.
        self.goto_chatgpt()

    def __del__(self):
        self.browser.close()

        if hasattr(self,'user_data_dir'):
            shutil.rmtree(self.user_data_dir)
