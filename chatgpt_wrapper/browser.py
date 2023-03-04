import shutil
import uuid
import json
import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright
from playwright._impl._api_structures import ProxySettings
from playwright.async_api._generated import BrowserType,BrowserContext
from .log import LogCapable

class AsyncBrowser(LogCapable):
    # A single play can launch many browsers
    play=None
    def __init__(self):
        self.browser:BrowserType=None
        self.browser_context:BrowserContext=None
        self.user_data_dir=None
        self.page=None
        self.session={}

    async def create(self,browser:str='firefox', headless:bool=True, proxy: Optional[ProxySettings] = None, debug_log=None):
        super().__init__(debug_log=debug_log)
        if AsyncBrowser.play is None:
            AsyncBrowser.play=await async_playwright().start()

        if not hasattr(self.play,browser):
            self.log.error("Browser %s is invalid, falling back on firefox. ",browser)
            browser='firefox'
        self.browser:BrowserType=getattr(self.play,browser)

        try:
            self.browser_context=await self.browser.lauch_persistent_context(
                user_data_dir="/tmp/playwright",
                headless=headless,
                proxy=proxy
            )
        except Exception:
            self.user_data_dir = f"/tmp/{str(uuid.uuid4())}"
            shutil.copytree("/tmp/playwright", self.user_data_dir)
            self.browser_context:BrowserContext = await self.browser.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                proxy=proxy,
            )

        self.page=await self.browser_context.new_page()
        await self.goto_chat()
        return self

    async def goto_chat(self,timeout=15):
        self.log.info("Going to ChatGPT website...")
        try:
            await self.page.goto("https://chat.openai.com")
            await self.page.wait_for_url("/chat",timeout=timeout*1000)
            self.log.info("ChatGPT website loaded. ")
        except Exception as err:
            self.log.error("Cannot load ChatGPT website. Currently at %s",self.page.url)
            raise err


    async def refresh_session(self,timeout=10):
        self.log.info("Refreshing session...")
        await self.page.goto("https://chat.openai.com/api/auth/session")
        try:
            await self.page.wait_for_url("/api/auth/session", timeout=timeout * 1000)
        except Exception as err:
            self.log.error("Timed out refreshing session. Page is now at %s. ")
            raise err

        try:
            while "Please stand by, while we are checking your browser..." in await self.page.content():
                await asyncio.sleep(1)
            contents = await self.page.content()
            """
            By GETting /api/auth/session, the server would ultimately return a raw json file.
            However, as this is a browser, it will add something to it, like <body> or so, like this:

            <html><head><link rel="stylesheet" href="resource://content-accessible/plaintext.css"></head><body><pre>{xxx:"xxx",{},accessToken="sdjlsfdkjnsldkjfslawefkwnlsdw"}
            </pre></body></html>

            The following code tries to extract the json part from the page, by simply finding the first `{` and the last `}`.
            """
            found_json = re.search('{.*}', contents)
            if found_json is None:
                self.log.error("JSON not found in refresh_session response. ")
                raise json.JSONDecodeError("Cannot find JSON in /api/auth/session 's response", contents, 0)
            contents = contents[found_json.start():found_json.end()]
            self.session = json.loads(contents)
            self.log.info("Succeessfully refreshed session. ")
        except json.JSONDecodeError as err:
            self.log.error("Failed to decode session key: %s. Maybe Access denied? ",err.msg)
            self.log.debug("Received contents: %s",contents)
            raise err

        # Now the browser should be at /api/auth/session
        # Go back to the chat page.
        await self.goto_chat()

        self.log.info("Succeeded refreshing session. ")


    async def cleanup(self):
        if self.user_data_dir:
            shutil.rmtree(self.user_data_dir)

        await self.browser_context.close()


