import os
import atexit
import base64
import json
from json.decoder import JSONDecodeError
import operator
import time
import uuid
import logging
import shutil
from functools import reduce
from time import sleep
from typing import Optional
from playwright.sync_api import sync_playwright
from playwright._impl._api_structures import ProxySettings

RENDER_MODELS = {
    "default": "text-davinci-002-render-sha",
    "legacy-paid": "text-davinci-002-render-paid",
    "legacy-free": "text-davinci-002-render"
}

DEFAULT_CONSOLE_LOG_LEVEL = logging.ERROR
DEFAULT_CONSOLE_LOG_FORMATTER = logging.Formatter("%(levelname)s - %(message)s")
DEFAULT_FILE_LOG_LEVEL = logging.DEBUG
DEFAULT_FILE_LOG_FORMATTER = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

class ChatGPT:
    """
    A ChatGPT interface that uses Playwright to run a browser,
    and interacts with that browser to communicate with ChatGPT in
    order to provide an open API to ChatGPT.
    """

    stream_div_id = "chatgpt-wrapper-conversation-stream-data"
    eof_div_id = "chatgpt-wrapper-conversation-stream-data-eof"
    session_div_id = "chatgpt-wrapper-session-data"
    chatgpt_url = "https://chat.openai.com/"

    def __init__(self, headless: bool = True, browser="firefox", model="default", timeout=60, debug_log=None, after_browser_launched_cb = None, proxy: Optional[ProxySettings] = None):
        self.log = self._set_logging(debug_log)
        self.log.info("ChatGPT initialized")
        self.play = sync_playwright().start()
        self.after_browser_launched_cb = after_browser_launched_cb
        try:
            playbrowser = getattr(self.play, browser)
        except Exception:
            print(f"Browser {browser} is invalid, falling back on firefox")
            playbrowser = self.play.firefox
        try:
            self.browser = playbrowser.launch_persistent_context(
                user_data_dir="/tmp/playwright",
                headless=headless,
                proxy=proxy,
            )
        except Exception:
            self.user_data_dir = f"/tmp/{str(uuid.uuid4())}"
            shutil.copytree("/tmp/playwright", self.user_data_dir)
            self.browser = playbrowser.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                proxy=proxy,
            )

        if len(self.browser.pages) > 0:
            self.page = self.browser.pages[0]
        else:
            self.page = self.browser.new_page()
        self._start_browser()
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.conversation_title_set = None
        self.session = None
        self.model = model
        self.timeout = timeout
        atexit.register(self._cleanup)

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

    def _start_browser(self):
        self.page.goto(self.__class__.chatgpt_url)
        if self.after_browser_launched_cb:
            self.after_browser_launched_cb(self.page)

    def _cleanup(self):
        self.browser.close()
        # remove the user data dir in case this is a second instance
        if hasattr(self, "user_data_dir"):
            shutil.rmtree(self.user_data_dir)
        self.play.stop()

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

    def _api_request_build_headers(self, custom_headers={}):
        headers = {
            "Authorization": "Bearer %s" % self.session["accessToken"],
        }
        headers.update(custom_headers)
        return headers

    def _process_api_response(self, url, response, method="GET"):
        self.log.debug(f"{method} {url} response, OK: {response.ok}, TEXT: {response.text()}")
        json = None
        if response.ok:
            try:
                json = response.json()
            except JSONDecodeError:
                pass
        if not response.ok or not json:
            self.log.debug(f"{response.status} {response.status_text} {response.headers}")
        return response.ok, json, response

    def _api_get_request(self, url, query_params={}, custom_headers={}):
        headers = self._api_request_build_headers(custom_headers)
        response = self.page.request.get(url, headers=headers, params=query_params)
        return self._process_api_response(url, response)

    def _api_post_request(self, url, data={}, custom_headers={}):
        headers = self._api_request_build_headers(custom_headers)
        response = self.page.request.post(url, headers=headers, data=data)
        return self._process_api_response(url, response, method="POST")

    def _api_patch_request(self, url, data={}, custom_headers={}):
        headers = self._api_request_build_headers(custom_headers)
        response = self.page.request.patch(url, headers=headers, data=data)
        return self._process_api_response(url, response, method="PATCH")

    def _gen_title(self):
        if not self.conversation_id or self.conversation_id and self.conversation_title_set:
            return
        url = f"https://chat.openai.com/backend-api/conversation/gen_title/{self.conversation_id}"
        data = {
            "message_id": self.parent_message_id,
            "model": RENDER_MODELS[self.model],
        }
        ok, json, response = self._api_post_request(url, data)
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

    def delete_conversation(self, uuid=None):
        if self.session is None:
            self.refresh_session()
        if not uuid and not self.conversation_id:
            return
        id = uuid if uuid else self.conversation_id
        url = f"https://chat.openai.com/backend-api/conversation/{id}"
        data = {
            "is_visible": False,
        }
        ok, json, response = self._api_patch_request(url, data)
        if ok:
            return json
        else:
            self.log.error("Failed to delete conversation")

    def set_title(self, title, conversation_id=None):
        if self.session is None:
            self.refresh_session()
        id = conversation_id if conversation_id else self.conversation_id
        url = f"https://chat.openai.com/backend-api/conversation/{id}"
        data = {
            "title": title,
        }
        ok, json, response = self._api_patch_request(url, data)
        if ok:
            return json
        else:
            self.log.error("Failed to set title")

    def get_history(self, limit=20, offset=0):
        if self.session is None:
            self.refresh_session()
        url = "https://chat.openai.com/backend-api/conversations"
        query_params = {
            "offset": offset,
            "limit": limit,
        }
        ok, json, response = self._api_get_request(url, query_params)
        if ok:
            history = {}
            for item in json["items"]:
                history[item["id"]] = item
            return history
        else:
            self.log.error("Failed to get history")

    def get_conversation(self, id=None):
        if self.session is None:
            self.refresh_session()
        id = id if id else self.conversation_id
        if id:
            url = f"https://chat.openai.com/backend-api/conversation/{id}"
            ok, json, response = self._api_get_request(url)
            if ok:
                return json
            else:
                self.log.error(f"Failed to get conversation {uuid}")

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
        start_time = time.time()
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
                chunk = full_event_message[len(last_event_msg):]
                last_event_msg = full_event_message
                yield chunk

            # if we saw the eof signal, this was the last event we
            # should process and we are done
            if len(eof_datas) > 0 or (((time.time() - start_time) > self.timeout) and full_event_message is None):
                break

            sleep(0.2)

        self._cleanup_divs()
        self._gen_title()

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
            else "Unusable response produced, maybe login session expired. Try 'pkill firefox' and 'chatgpt install'"
        )

    def new_conversation(self):
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.conversation_title_set = None
