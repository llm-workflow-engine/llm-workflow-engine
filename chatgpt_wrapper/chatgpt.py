""" ChatGPT class
"""
import atexit
import base64
import json
from json.decoder import JSONDecodeError
import time
import uuid
import logging
import shutil
import time
import datetime
import threading
from typing import Optional
from playwright.sync_api import sync_playwright
from playwright._impl._api_structures import ProxySettings
# from . import error
import error

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
    error_div_id = "chatgpt-wrapper-error-data"
    lock=threading.Lock()
    browser=None
    page=None
    enabled=True
    session={}

    def __init__(self, headless: bool = True, browser="firefox", model="default", timeout=60, debug_log=None, proxy: Optional[ProxySettings] = None):
        """Create an ChatGPT asynchronously

        Args:
            headless (bool, optional): Start headless (no GUI) browser. Defaults to True.
            browser (str, optional): Which browser to use. Defaults to "firefox".
            timeout (int, optional): Timeout waiting for ChatGPT to generate message. Defaults to 60.
            proxy (Optional[ProxySettings], optional): Network proxy. Will be passwd to playwright. Defaults to None.
            instance (object, optional): If you already have an instance, pass it here. Used in the synchronous API. When set to None, create a new one. Defaults to None.

        """
        self.log = self._set_logging(debug_log)
        self.log.info("ChatGPT initialized")
        self.play = sync_playwright().start()
        try:
            playbrowser = getattr(self.play, browser)
        except Exception:
            self.log.error(f"Browser {browser} is invalid, falling back on firefox")
            playbrowser = self.play.firefox

        if ChatGPT.browser==None:
            try:
                ChatGPT.browser = playbrowser.launch_persistent_context(
                    user_data_dir="/tmp/playwright",
                    headless=headless,
                    proxy=proxy,
                )
            except Exception:
                self.user_data_dir = f"/tmp/{str(uuid.uuid4())}"
                self.log.warning(f"Failed to launch browser at /tmp/playwright. Launching at {self.user_data_dir}")
                shutil.copytree("/tmp/playwright", self.user_data_dir)
                self.browser = playbrowser.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=headless,
                    proxy=proxy,
                )
        if ChatGPT.page==None:
            ChatGPT.page=ChatGPT.browser.new_page()
            self._start_browser()

        js_logger=logging.getLogger("js console")
        js_logger.setLevel(logging.INFO)
        def js_log(msg):
            if '[JavaScript Error:' in msg.text: return
            if '[JavaScript Warning:' in msg.text: return
            if msg.type in ['log','info']: js_logger.info(msg.text)
            elif msg.type=='debug': js_logger.debug(msg.text)
            elif msg.type=='warning': js_logger.warning(msg.text)
            elif msg.type=='error': js_logger.error(msg.text)
            else: js_logger.info(msg.text)
        self.page.on("console", js_log)
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.conversation_title_set = None
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
        self.log.info("Loading ChatGPT webpage...")
        ChatGPT.page.goto("https://chat.openai.com/")
        try:
            ChatGPT.page.wait_for_url("/chat")
        except Exception:
            errors=ChatGPT.page.query_selector_all("div.cf-error-details")
            if len(errors)>0 and 'Access denied' in errors[0].inner_html():
                self.log.error("Got Access denied. Self-disabling for 10 minutes. ")
                ChatGPT.enabled=False
                time.sleep(10*60)
                ChatGPT.enabled=True
                return self._start_browser()
        self.log.info("ChatGPT webpage loaded")

    def _cleanup(self):
        self.browser.close()
        # remove the user data dir in case this is a second instance
        if hasattr(self, "user_data_dir"):
            shutil.rmtree(self.user_data_dir)
        self.play.stop()
    def refresh_session(self,timeout=20,remaining_retry=5):
        self.log.info("Refreshing session")
        if remaining_retry==0:
            self.log.error("Cannot refresh session. ")
            raise error.NetworkError("Cannot refresh session. ")
        self.page.evaluate(
            """
            const xhr = new XMLHttpRequest();
            xhr.open('GET', 'https://chat.openai.com/api/auth/session');
            xhr.onload = () => {
                if(xhr.status == 200) {
                    let mydiv = document.createElement('DIV');
                    mydiv.id = "SESSION_DIV_ID"
                    mydiv.innerHTML = xhr.responseText;
                    document.body.appendChild(mydiv);
                }else{
                    let err = document.createElement('div')
                    err.id=ERROR_DIV_ID
                    console.error(xhr)
                    document.body.appendChild(err)
                }
            };
            xhr.send();
            """
            .replace("SESSION_DIV_ID", self.session_div_id)
            .replace("ERROR_DIV_ID", self.error_div_id)
        )
        starttime=datetime.datetime.now()
        while (datetime.datetime.now()-starttime).total_seconds()<=timeout:
            session_datas = self.page.query_selector_all(f"div#{self.session_div_id}")
            error_datas = self.page.query_selector_all(f"div#{self.error_div_id}")
            if len(session_datas) > 0:
                session_data = json.loads(session_datas[0].inner_text())
                self.session = session_data
                self.page.evaluate(f"document.getElementById('{self.session_div_id}').remove()")
                return

            elif len(error_datas) > 0:
                self.log.warning("Refreshing session failed. Retrying...")
                self.page.evaluate(f"document.getElementById('{self.error_div_id}').remove()")
                # break and retry
                break
            time.sleep(0.2)
        else:
            logging.warning("Refreshing session timed out. Retrying...")

        # Try again
        self.refresh_session(remaining_retry=remaining_retry-1)
        return



    def _cleanup_divs(self):
        try:
            self.page.evaluate(f"document.getElementById('{self.stream_div_id}').remove()")
            self.page.evaluate(f"document.getElementById('{self.eof_div_id}').remove()")
        except Exception as err:
            self.log.error("Failed to clean up divs: \n%s", err)

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

    def delete_conversation(self, uuid=None):
        if 'accessToken' not in self.session:
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
        if 'accessToken' not in self.session:
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
        if 'accessToken' not in self.session:
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

    def ask_stream(self, prompt: str, remaining_retry=2):
        """Ask ChatGPT something by sending XHR requests. Response is streamed

        Example:
        ```python3
        for chunk in gpt.ask_stream("Good night!"):
            # chunk will be, for example, one or a few words
            print(chunk,end='',flush=True)
        ```

        Args:
            prompt (str): Prompt to give to ChatGPT
            remaining_retry (int): How many retries remaining

        Raises:
            error.NotLoggedInError: Session is not useable. You need to log in.

        Yields:
            str: The response from ChatGPT.
        """
        if self.session == {}:
            self.refresh_session()

        new_message_id = str(uuid.uuid4())

        if "accessToken" not in self.session:
            self.log.error("Session not usable. You need to log in. ")
            raise error.NotLoggedInError(
                "Your ChatGPT session is not usable.\n"
                "* Run this program with the `install` parameter and log in to ChatGPT.\n"
                "* If you think you are already logged in, try running the `session` command."
            )

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
                console.error(err);
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
            """
            .replace("BEARER_TOKEN", self.session["accessToken"])
            .replace("REQUEST_JSON", json.dumps(request))
            .replace("STREAM_DIV_ID", self.stream_div_id)
            .replace("EOF_DIV_ID", self.eof_div_id)
        )
        try:
            self.page.evaluate(code)
        except Exception as err:
            self.log.warning("Error occurred when asking ChatGPT (Retrying...): %s",err)
            self.refresh_session()
            for i in self.ask_stream(prompt,remaining_retry=remaining_retry-1):
                yield i
            return

        last_event_msg = ""
        start_time = time.time()
        full_event_message = None
        while time.time() - start_time <= self.timeout or full_event_message != None:
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
            except Exception as err:
                logging.error("Failed to read response from ChatGPT: %s",err)
                raise error.ChatGPTResponseError(
                    "Failed to read response from ChatGPT.  Tips:\n"
                    " * Try again.  ChatGPT can be flaky.\n"
                    " * Use the `session` command to refresh your session, and then try again.\n"
                    " * Restart the program in the `install` mode and make sure you are logged in."
                )

            if full_event_message is not None:
                chunk = full_event_message[len(last_event_msg):]
                last_event_msg = full_event_message
                self.log.info("< (ChatGPT) %s",chunk)
                yield chunk

            # if we saw the eof signal, this was the last event we
            # should process and we are done
            if len(eof_datas)>0:
                break

            time.sleep(0.2)
        else:
            # Timeout
            self.log.error("Timeout when asking ChatGPT. Retrying...")
            self.refresh_session()
            for chunk in self.ask_stream(prompt=prompt,remaining_retry=remaining_retry-1):
                yield chunk
            return

        self._cleanup_divs()

    def ask_stream_clicking(self, prompt: str, remaining_retry=2):
        """Ask ChatGPT by clicking the buttons on the website. Response is streamed.

        Example:
        ```python3
        for chunk in gpt.ask_stream("Good night!"):
            # chunk will be, for example, one or a few words
            print(chunk,end='',flush=True)
        ```

        Args:
            prompt (str): Prompt to give to ChatGPT
            remaining_retry (int): How many retries remaining

        Raises:
            error.NotLoggedInError: Session is not useable. You need to log in.

        Yields:
            str: Chunks of response
        """
        if remaining_retry==0:
            self.log.error("Cannot ask ChatGPT. ")
            raise error.NetworkError("Cannot ask ChatGPT. ")
        if 'accessToken' not in self.session:
            self.refresh_session()

        if "accessToken" not in self.session:
            self.log.error("Session not usable. You need to log in. ")
            raise error.NotLoggedInError(
                "Your ChatGPT session is not usable.\n"
                "* Run this program with the `install` parameter and log in to ChatGPT.\n"
                "* If you think you are already logged in, try running the `session` command."
            )

        prompt=prompt.replace('\n','\\n')

        code = (
            f"""
            let bottom=document.getElementsByTagName("textarea")[0].parentElement
            let textbox=bottom.children[0]
            let ask_btn=bottom.children[1]

            textbox.value="{prompt}"


            ask_btn.click()
            setTimeout(function(){{
                let answers=document.getElementsByClassName("bg-gray-50")
                let answer=answers[answers.length-1]

                let response_store = document.createElement('div')
                response_store.id = "{self.stream_div_id}"
                response_store.innerHTML = answer.innerText
                document.body.appendChild(response_store)

                let check_done=function(){{
                    let outer_judges=answer.getElementsByClassName("justify-between")[0]
                    let inner_judges=outer_judges.getElementsByTagName("div")[0]
                    if(inner_judges.classList.contains("visible")){{
                        // Done
                        let done_sign=document.createElement('div')
                        response_store.innerHTML = answer.innerText
                        done_sign.id="{self.eof_div_id}"
                        document.body.appendChild(done_sign)
                    }}else{{
                        // Not done yet
                        response_store.innerHTML = answer.innerText
                        setTimeout(check_done,200)
                    }}
                }}

                check_done()
            }},300)
            """
        )

        try:
            self.page.evaluate(code)
        except Exception as err:
            self.log.warning("Error occurred when asking ChatGPT (Retrying...): %s",err)
            self.refresh_session()
            for i in self.ask_stream_clicking(prompt):
                yield i
            return

        time.sleep(0.3) # Wait for response container to be created

        last_event_msg = ""
        start_time = time.time()
        response=""
        while time.time() - start_time <= self.timeout or response!="":
            eof_datas = self.page.query_selector_all(f"div#{self.eof_div_id}")

            response_container = self.page.query_selector_all(
                f"div#{self.stream_div_id}"
            )
            response=response_container[0].inner_text()
            response=response.replace('\u200b','')

            if len(response) > 0:
                chunk = response[len(last_event_msg):]
                last_event_msg = response
                print(chunk,end='',flush=True)

                if 'An error occurred. If this issue persists please contact us through' in response or\
                    'The server had an error while processing your request.' in response:
                    print("Error detected when receiving response")
                    self.log.error("ChatGPT gave an Error (Retrying...): %s",response)
                    # TODO: Choose the right conversation
                    self.page.reload()
                    time.sleep(10)
                    for i in self.ask_stream_clicking(prompt,remaining_retry=remaining_retry-1):
                        yield i
                    return

                self.log.info("< (ChatGPT) %s",chunk)
                yield chunk

            # if we saw the eof signal, this was the last event we
            # should process and we are done
            if len(eof_datas) > 0:
                break

            time.sleep(0.2)
        else:
            # Timeout
            self.log.error("Timed out waiting for ChatGPT response. ")
            self.page.reload()
            time.sleep(10)
            for i in self.ask_stream_clicking(prompt,remaining_retry=remaining_retry-1):
                yield i
            return

        self._cleanup_divs()
        self._gen_title()


    def ask(self, message: str, remaining_retry=2) -> str:
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.
            remaining_retry (int): How many retries left

        Returns:
            str: The response received from OpenAI.
        """
        if remaining_retry==0:
            self.log.error("Cannot ask ChatGPT. Repeatedly receiving empty response. ")
            raise error.ChatGPTResponseError("Cannot ask ChatGPT. Repeatedly receiving empty response. ")

        response = [i for i in self.ask_stream(message)]
        if len(response)!=0:
            return ''.join(response)
        # Else: retry
        self.log.error("Received empty response from ChatGPT. Retrying... ")
        self.refresh_session()
        return self.ask(message,remaining_retry=remaining_retry-1)

    def new_conversation(self):
        self.parent_message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.conversation_title_set = None



def main():
    gpt=ChatGPT(headless=False)
    # loop=asyncio.get_event_loop()
    # prompt=input("> ")
    prompt="Good night!"
    while prompt!='exit':
        prompt=input("> ")
        if prompt=='delete':
            gpt.delete_conversation()
        elif prompt=='title':
            gpt._gen_title()
        elif prompt=='history':
            print(gpt.get_history())
        else:
            print('< ',end='',flush=True)
            print(gpt.ask(prompt))
            print('')

if __name__=='__main__':
    main()

