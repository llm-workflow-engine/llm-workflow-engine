import asyncio
import signal
import atexit
import base64
import json
import time
import uuid
import logging
import re
import shutil
from typing import Optional
from playwright.async_api import async_playwright
from playwright._impl._api_structures import ProxySettings

import nest_asyncio
nest_asyncio.apply()

RENDER_MODELS = {
    "default": "text-davinci-002-render-sha",
    "legacy-paid": "text-davinci-002-render-paid",
    "legacy-free": "text-davinci-002-render"
}

DEFAULT_CONSOLE_LOG_LEVEL = logging.ERROR
DEFAULT_CONSOLE_LOG_FORMATTER = logging.Formatter("%(levelname)s - %(message)s")
DEFAULT_FILE_LOG_LEVEL = logging.DEBUG
DEFAULT_FILE_LOG_FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

class AsyncChatGPT:
    """
    A ChatGPT interface that uses Playwright to run a browser,
    and interacts with that browser to communicate with ChatGPT in
    order to provide an open API to ChatGPT.
    """

    stream_div_id = "chatgpt-wrapper-conversation-stream-data"
    eof_div_id = "chatgpt-wrapper-conversation-stream-data-eof"
    interrupt_div_id = "chatgpt-wrapper-conversation-stream-data-interrupt"
    session_div_id = "chatgpt-wrapper-session-data"


    async def create(self, headless: bool = True, browser="firefox", timeout=60, proxy: Optional[ProxySettings] = None):
        self.streaming = False
        self._setup_signal_handlers()
        self.lock = asyncio.Lock()
        self.play = await async_playwright().start()
        try:
            playbrowser = getattr(self.play, browser)
        except Exception:
            print(f"Browser {browser} is invalid, falling back on firefox")
            playbrowser = self.play.firefox
        try:
            self.browser = await playbrowser.launch_persistent_context(
                user_data_dir="/tmp/playwright",
                headless=headless,
                proxy=proxy,
            )
        except Exception:
            self.user_data_dir = f"/tmp/{str(uuid.uuid4())}"
            shutil.copytree("/tmp/playwright", self.user_data_dir)
            self.browser = await playbrowser.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                proxy=proxy,
            )

        if len(self.browser.pages) > 0:
            self.page = self.browser.pages[0]
        else:
            self.page = await self.browser.new_page()
        await self._start_browser()
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.conversation_title_set = None
        self.session = None
        self.timeout = timeout
        atexit.register(self._shutdown)

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGUSR1, self.terminate_stream)

    def _shutdown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(self._cleanup()))

    def _set_logging(self, debug_log):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.DEBUG)
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(DEFAULT_CONSOLE_LOG_FORMATTER)
        log_console_handler.setLevel(DEFAULT_CONSOLE_LOG_LEVEL)
        logger.addHandler(log_console_handler)
        if debug_log:
            log_file_handler = logging.FileHandler(debug_log)
            log_file_handler.setFormatter(DEFAULT_FILE_LOG_FORMATTER)
            log_file_handler.setLevel(DEFAULT_FILE_LOG_LEVEL)
            logger.addHandler(log_file_handler)
        return logger

    async def _start_browser(self):
        await self.page.goto("https://chat.openai.com/")

    async def _cleanup(self):
        await self.browser.close()
        # remove the user data dir in case this is a second instance
        if hasattr(self, "user_data_dir"):
            shutil.rmtree(self.user_data_dir)
        await self.play.stop()

    async def refresh_session(self, timeout=15):
        """Refresh session, by redirecting the *page* to /api/auth/session rather than a simple xhr request.

        In this way, we can pass the browser check.

        Args:
            timeout (int, optional): Timeout waiting for the refresh in seconds. Defaults to 10.
        """
        self.log.info("Refreshing session...")
        await self.page.goto("https://chat.openai.com/api/auth/session")
        try:
            await self.page.wait_for_url("/api/auth/session", timeout=timeout * 1000)
        except Exception:
            self.log.error("Timed out refreshing session. Page is now at %s. Calling _start_browser()...")
            await self._start_browser()
        try:
            while "Please stand by, while we are checking your browser..." in await self.page.content():
                time.sleep(1)
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
                raise json.JSONDecodeError("Cannot find JSON in /api/auth/session 's response", contents, 0)
            contents = contents[found_json.start():found_json.end()]
            self.log.debug("Refreshing session received: %s", contents)
            self.session = json.loads(contents)
            self.log.info("Succeessfully refreshed session. ")
        except json.JSONDecodeError:
            self.log.error("Failed to decode session key. Maybe Access denied? ")

        # Now the browser should be at /api/auth/session
        # Go back to the chat page.
        await self._start_browser()

    async def _cleanup_divs(self):
        await self.page.evaluate(f"document.getElementById('{self.stream_div_id}').remove()")
        code = (
            """
            const eof_div = document.getElementById('EOF_DIV_ID');
            if(typeof eof_div !== 'undefined' && eof_div !== null) {
              eof_div.remove();
            }
            """
        ).replace("EOF_DIV_ID", self.eof_div_id)
        await self.page.evaluate(code)

    def _api_request_build_headers(self, custom_headers={}):
        headers = {
            "Authorization": "Bearer %s" % self.session["accessToken"],
        }
        headers.update(custom_headers)
        return headers

    async def _process_api_response(self, url, response, method="GET"):
        self.log.debug(f"{method} {url} response, OK: {response.ok}, TEXT: {await response.text()}")
        json = None
        if response.ok:
            try:
                json = await response.json()
            except JSONDecodeError:
                pass
        if not response.ok or not json:
            self.log.debug(f"{response.status} {response.status_text} {response.headers}")
        return response.ok, json, response

    async def _api_get_request(self, url, query_params={}, custom_headers={}):
        headers = self._api_request_build_headers(custom_headers)
        response = await self.page.request.get(url, headers=headers, params=query_params)
        return await self._process_api_response(url, response)

    async def _api_post_request(self, url, data={}, custom_headers={}):
        headers = self._api_request_build_headers(custom_headers)
        response = await self.page.request.post(url, headers=headers, data=data)
        return await self._process_api_response(url, response, method="POST")

    async def _api_patch_request(self, url, data={}, custom_headers={}):
        headers = self._api_request_build_headers(custom_headers)
        response = await self.page.request.patch(url, headers=headers, data=data)
        return await self._process_api_response(url, response, method="PATCH")

    async def _gen_title(self):
        if not self.conversation_id or self.conversation_id and self.conversation_title_set:
            return
        url = f"https://chat.openai.com/backend-api/conversation/gen_title/{self.conversation_id}"
        data = {
            "message_id": self.parent_message_id,
            "model": RENDER_MODELS[self.model],
        }
        ok, json, response = await self._api_post_request(url, data)
        if ok:
            # TODO: Do we want to do anything with the title we got back?
            # response_data = response.json()
            self.conversation_title_set = True
        else:
            self.log.warning("Failed to auto-generate title for new conversation")

    def conversation_data_to_messages(self, conversation_data):
        mapping_dict = conversation_data['mapping']
        messages = []
        parent_id = None
        while True:
            current_item = next((item for item in mapping_dict.values() if item['parent'] == parent_id), None)
            if current_item is None:
                return messages
            message = current_item['message']
            if message is not None and 'author' in message and message['author']['role'] != 'system':
                messages.append(current_item['message'])
            parent_id = current_item['id']

    async def delete_conversation(self, uuid=None):
        if self.session is None:
            await self.refresh_session() if asyncio.iscoroutinefunction(self.refresh_session) else self.refresh_session()
        if not uuid and not self.conversation_id:
            return
        id = uuid if uuid else self.conversation_id
        url = f"https://chat.openai.com/backend-api/conversation/{id}"
        data = {
            "is_visible": False,
        }
        ok, json, response = await self._api_patch_request(url, data)
        if ok:
            return json
        else:
            self.log.error("Failed to delete conversation")

    async def set_title(self, title, conversation_id=None):
        if self.session is None:
            await self.refresh_session() if asyncio.iscoroutinefunction(self.refresh_session) else self.refresh_session()
        id = conversation_id if conversation_id else self.conversation_id
        url = f"https://chat.openai.com/backend-api/conversation/{id}"
        data = {
            "title": title,
        }
        ok, json, response = await self._api_patch_request(url, data)
        if ok:
            return json
        else:
            self.log.error("Failed to set title")

    async def get_history(self, limit=20, offset=0):
        if self.session is None:
            await self.refresh_session() if asyncio.iscoroutinefunction(self.refresh_session) else self.refresh_session()
        url = "https://chat.openai.com/backend-api/conversations"
        query_params = {
            "offset": offset,
            "limit": limit,
        }
        ok, json, response = await self._api_get_request(url, query_params)
        if ok:
            history = {}
            for item in json["items"]:
                history[item["id"]] = item
            return history
        else:
            self.log.error("Failed to get history")

    async def get_conversation(self, uuid=None):
        if self.session is None:
            await self.refresh_session() if asyncio.iscoroutinefunction(self.refresh_session) else self.refresh_session()
        uuid = uuid if uuid else self.conversation_id
        if uuid:
            url = f"https://chat.openai.com/backend-api/conversation/{uuid}"
            ok, json, response = await self._api_get_request(url)
            if ok:
                return json
            else:
                self.log.error(f"Failed to get conversation {uuid}")

    async def ask_stream(self, prompt: str):
        if self.session is None:
            await self.refresh_session() if asyncio.iscoroutinefunction(self.refresh_session) else self.refresh_session()

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
            "model": RENDER_MODELS[self.model],
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
              const interrupt_div = document.getElementById('INTERRUPT_DIV_ID');
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
                  newEvent = undefined;
                }
                if(newEvent !== undefined) {
                  stream_div.innerHTML = btoa(newEvent);
                  xhr.seenBytes = xhr.responseText.length;
                }
              }
              if(xhr.readyState == 4 && (typeof interrupt_div === 'undefined' || interrupt_div === null)) {
                const eof_div = document.createElement('DIV');
                eof_div.id = "EOF_DIV_ID";
                document.body.appendChild(eof_div);
              }
              if(typeof interrupt_div !== 'undefined' && interrupt_div !== null) {
                console.warning('Interrupting stream');
                xhr.abort();
                interrupt_div.remove();
              }
            };
            xhr.send(JSON.stringify(REQUEST_JSON));
            """.replace(
                "BEARER_TOKEN", self.session["accessToken"]
            )
            .replace("REQUEST_JSON", json.dumps(request))
            .replace("STREAM_DIV_ID", self.stream_div_id)
            .replace("EOF_DIV_ID", self.eof_div_id)
            .replace("INTERRUPT_DIV_ID", self.interrupt_div_id)
        )

        self.streaming = True
        await self.page.evaluate(code)

        last_event_msg = ""
        start_time = time.time()
        while True:
            if not self.streaming:
                self.log.info("Request to interrupt streaming")
                await self.interrupt_stream()
                break
            eof_datas = await self.page.query_selector_all(f"div#{self.eof_div_id}")

            conversation_datas = await self.page.query_selector_all(
                f"div#{self.stream_div_id}"
            )
            if len(conversation_datas) == 0:
                continue

            full_event_message = None

            try:
                event_raw = base64.b64decode(await conversation_datas[0].inner_html())
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
                chunk = full_event_message[len(last_event_msg):]
                last_event_msg = full_event_message
                yield chunk

            # if we saw the eof signal, this was the last event we
            # should process and we are done
            if len(eof_datas) > 0 or (((time.time() - start_time) > self.timeout) and full_event_message is None):
                break

            await asyncio.sleep(0.2)

        if not self.streaming:
            yield (
                "\nGeneration stopped\n"
            )
        self.streaming = False
        await self._cleanup_divs()
        await self._gen_title()

    async def interrupt_stream(self):
        self.log.info("Interrupting stream")
        code = (
            """
            const interrupt_div = document.createElement('DIV');
            interrupt_div.id = "INTERRUPT_DIV_ID";
            document.body.appendChild(interrupt_div);
            """
        ).replace("INTERRUPT_DIV_ID", self.interrupt_div_id)
        await self.page.evaluate(code)

    def terminate_stream(self, _signal, _frame):
        self.log.info("Received signal to terminate stream")
        if self.streaming:
            self.streaming = False

    async def ask(self, message: str) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        async with self.lock:
            response = list([i async for i in self.ask_stream(message)])
            if len(response) == 0:
                return "Unusable response produced, maybe login session expired. Try 'pkill firefox' and 'chatgpt install'"
            else:
                return ''.join(response)

    def new_conversation(self):
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.conversation_title_set = None

class ChatGPT(AsyncChatGPT):

    def __init__(self, headless: bool = True, browser="firefox", model="default", timeout=60, debug_log=None, proxy: Optional[ProxySettings] = None):
        self.model = model
        self.log = self._set_logging(debug_log)
        self.log.info("ChatGPT initialized")
        asyncio.run(super().create(headless, browser, timeout, proxy))

    def refresh_session(self):
        return asyncio.run(super().refresh_session())

    def ask_stream(self, prompt: str):
        def iter_over_async(ait):
            loop = asyncio.get_event_loop()
            ait = ait.__aiter__()
            async def get_next():
                try:
                    obj = await ait.__anext__()
                    return False, obj
                except StopAsyncIteration:
                    return True, None
            while True:
                done, obj = loop.run_until_complete(get_next())
                if done:
                    break
                yield obj
        yield from iter_over_async(super().ask_stream(prompt))

    def ask(self, message: str) -> str:
        return asyncio.run(super().ask(message))

    def get_conversation(self, uuid=None):
        return asyncio.run(super().get_conversation(uuid))

    def delete_conversation(self, uuid=None):
        return asyncio.run(super().delete_conversation(uuid))

    def set_title(self, title, conversation_id=None):
        return asyncio.run(super().set_title(title, conversation_id))

    def get_history(self, limit=20, offset=0):
        return asyncio.run(super().get_history(limit, offset))
