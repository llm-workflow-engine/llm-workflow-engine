import os
import atexit
import base64
import json
import random
import string
import time
import datetime
import uuid
import re
import shutil
from playwright.sync_api import sync_playwright
from playwright._impl._api_structures import ProxySettings

from typing import Optional

from langchain.schema import HumanMessage

from chatgpt_wrapper.core.backend import Backend
from chatgpt_wrapper.core.plugin_manager import PluginManager
from chatgpt_wrapper.core.provider_manager import ProviderManager
from chatgpt_wrapper.core import util

GEN_TITLE_TIMEOUT = 5000

PROVIDER_BROWSER = "provider_chatgpt_browser"
ADDITIONAL_PLUGINS = [
    PROVIDER_BROWSER,
]

class BrowserBackend(Backend):
    """
    A ChatGPT interface that uses Playwright to run a browser,
    and interacts with that browser to communicate with ChatGPT in
    order to provide an open API to ChatGPT.
    """

    name = "chatgpt-browser"
    stream_div_id = "chatgpt-wrapper-conversation-stream-data"
    eof_div_id = "chatgpt-wrapper-conversation-stream-data-eof"
    interrupt_div_id = "chatgpt-wrapper-conversation-stream-data-interrupt"
    session_div_id = "chatgpt-wrapper-session-data"

    def __init__(self, config=None):
        super().__init__(config)
        self.play = None
        self.user_data_dir = None
        self.page = None
        self.browser = None
        self.session = None
        self.original_model = None
        self.override_llm = None
        self.plugin_manager = PluginManager(self.config, self, additional_plugins=ADDITIONAL_PLUGINS)
        self.provider_manager = ProviderManager(self.config, self.plugin_manager)
        self.set_provider()
        self.set_available_models()
        self.init_model()
        self.plugin_ids = self.config.get('browser.plugins')
        self.new_conversation()

    def init_model(self):
        default_preset = self.config.get('model.default_preset')
        if default_preset:
            success, new_value, user_message = self.set_model(default_preset)
            if success:
                return
            util.print_status_message(False, f"Failed to load default preset {default_preset}: {user_message}")
        self.set_model(self.provider.default_model)

    def set_provider(self):
        success, provider, user_message = self.provider_manager.load_provider(PROVIDER_BROWSER)
        if success:
            self.provider_name = PROVIDER_BROWSER
            self.provider = provider
        return success, provider, user_message

    def set_override_llm(self, preset_name=None):
        if preset_name:
            if preset_name not in self.provider.available_models:
                return False, None, f"Preset {preset_name} not an available model"
            customizations = {'model_name': preset_name}
            if self.should_stream():
                self.log.debug("Adding streaming-specific customizations to LLM request")
                customizations.update(self.streaming_args(interrupt_handler=True))
            self.override_llm = self.provider.make_llm(customizations, use_defaults=True)
            self.original_model = self.model
            self.model = preset_name
            message = f"Set override LLM based on preset {preset_name}"
            self.log.debug(message)
            return True, self.override_llm, message
        else:
            self.override_llm = None
            self.model = self.original_model
            self.original_model = None
            message = "Unset override LLM"
            self.log.debug(message)
            return True, None, message

    def get_primary_profile_directory(self):
        primary_profile = os.path.join(self.config.data_profile_dir, "playwright")
        return primary_profile

    def launch_browser_context(self, user_data_dir):
        browser = self.config.get('browser.provider')
        headless = not self.config.get('browser.debug')
        try:
            playbrowser = getattr(self.play, browser)
        except Exception:
            print(f"Browser {browser} is invalid, falling back on firefox")
            playbrowser = self.play.firefox
        self.browser = playbrowser.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            proxy=self.browser_proxy,
            handle_sigint=False,
        )

    def launch_browser(self, timeout=60, proxy: Optional[ProxySettings] = None):
        primary_profile = self.get_primary_profile_directory()
        self.streaming = False
        self.browser_proxy = proxy
        self.play = sync_playwright().start()
        try:
            self.launch_browser_context(primary_profile)
        except Exception:
            self.user_data_dir = f"{primary_profile}-{str(uuid.uuid4())}"
            message = f"Unable to launch browser from primary profile, trying alternate profile {self.user_data_dir}"
            print(message)
            self.log.warning(message)
            shutil.copytree(primary_profile, self.user_data_dir, ignore=shutil.ignore_patterns("lock"))
            self.launch_browser_context(self.user_data_dir)
        atexit.register(self._shutdown)

        if len(self.browser.pages) > 0:
            self.page = self.browser.pages[0]
        else:
            self.page = self.browser.new_page()
        self._start_browser()
        self.timeout = timeout
        self.log.info("ChatGPT browser initialized")
        return self

    def destroy_primary_profile(self):
        primary_profile = self.get_primary_profile_directory()
        shutil.rmtree(primary_profile)
        message = f"Destroyed primary profile: {primary_profile}"
        print(message)
        self.log.info(message)

    def _shutdown(self):
        self.cleanup()

    def _start_browser(self):
        self.page.goto("https://chat.openai.com/")

    def _handle_error(self, obj, response, message):
        full_message = f"{message}: {obj.error} {obj.message}, full response: {response}"
        self.log.error(full_message)
        return False, obj, full_message

    def cleanup(self):
        self.log.info("Cleaning up")
        if self.page and not self.page.is_closed():
            self.log.debug("Closing browser page")
            self.page.close()
        if self.browser and self.browser.pages:
            self.log.debug("Closing browser context")
            self.browser.close()
        # remove the user data dir in case this is a second instance
        if self.user_data_dir:
            self.log.info(f"Removing user data dir: {self.user_data_dir}")
            shutil.rmtree(self.user_data_dir)
        self.log.debug("Closing Playwright")
        self.play.stop()

    def get_runtime_config(self):
        output = """
* Model customizations:
  * Model: %s
""" % (self.model)
        return output

    def refresh_session(self, timeout=15):
        """Refresh session, by redirecting the *page* to /api/auth/session rather than a simple xhr request.

        In this way, we can pass the browser check.

        Args:
            timeout (int, optional): Timeout waiting for the refresh in seconds. Defaults to 15.
        """
        self.log.info("Refreshing session...")
        self.page.goto("https://chat.openai.com/api/auth/session")
        try:
            self.page.wait_for_url("/api/auth/session", timeout=timeout * 1000)
        except Exception:
            self.log.error("Timed out refreshing session. Page is now at %s. Calling _start_browser()...")
            self._start_browser()
        try:
            while "Please stand by, while we are checking your browser..." in self.page.content():
                time.sleep(1)
            contents = self.page.content()
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
        self._start_browser()

    def _cleanup_divs(self):
        self.page.evaluate(f"document.getElementById('{self.stream_div_id}').remove()")
        code = (
            """
            const eof_div = document.getElementById('EOF_DIV_ID');
            if(typeof eof_div !== 'undefined' && eof_div !== null) {
              eof_div.remove();
            }
            """
        ).replace("EOF_DIV_ID", self.eof_div_id)
        self.page.evaluate(code)

    def _api_request_build_headers(self, custom_headers=None):
        custom_headers = custom_headers or {}
        headers = {
            "Authorization": f"Bearer {self.session['accessToken']}",
            "Content-Type": "application/json",
        }
        headers.update(custom_headers)
        return headers

    def _process_api_response(self, url, response, method="GET"):
        self.log.debug(f"{method} {url}, JSON: {response}")
        if not response or 'error' in response:
            if not response:
                response = {"error": "unknown", "message": "Could not parse JSON response"}
            message = f"API response errror: {response['error']} {response['message']}"
            self.log.error(message)
            return False, response, message
        return True, response, "API request successful"

    def _api_xhr_request(self, method, url, query_params=None, data=None, headers=None, timeout=None):
        query_params = query_params or {}
        data = data or {}
        headers = headers or {}
        self.log.debug(f"Starting XHR request with METHOD: {method}, URL: {url}, QUERY_PARAMS: {query_params}, DATA: {data}, HEADERS: {headers}, TIMEOUT: {timeout}")
        random_fn_name = ''.join(random.choices(string.ascii_letters, k=20))
        js_function = f"""
        async function (method, url, query_params, data, headers, timeout) {{
            console.debug('Starting {random_fn_name} with method:', method, 'url:', url, 'query_params:', query_params, 'data:', data, 'headers:', headers, 'timeout:', timeout);
            const final_url = new URL(url);
            final_url.search = new URLSearchParams(query_params).toString();
            return new Promise((resolve, reject) => {{
                const xhr = new XMLHttpRequest();
                xhr.open(method, final_url, true);
                console.debug('Opened XHR request, method:', method, 'final_url:', final_url);
                for (const [key, value] of Object.entries(headers)) {{
                    console.debug('Setting header:', key, '=', value);
                    xhr.setRequestHeader(key, value);
                }}
                if (timeout !== null) {{
                    console.debug('Setting timeout:', timeout);
                    xhr.timeout = timeout * 1000;
                }}
                xhr.onload = function() {{
                    if (xhr.status >= 200 && xhr.status < 400) {{
                        console.debug('XHR request succeeded with status:', xhr.status, 'response:', xhr.responseText);
                        resolve(JSON.parse(xhr.responseText));
                    }} else {{
                        console.error('XHR request failed with status:', xhr.status, 'statusText:', xhr.statusText);
                        reject({{error: xhr.status, message: xhr.statusText}});
                    }}
                }};
                xhr.onerror = function() {{
                    console.error('XHR request encountered an error with status:', xhr.status, 'statusText:', xhr.statusText);
                    reject({{error: xhr.status, message: xhr.statusText}});
                }};
                xhr.ontimeout = function() {{
                    console.error('XHR request timed out with status:', xhr.status);
                    reject({{error: xhr.status, message: 'Request timed out'}});
                }};
                if (['PATCH', 'POST'].includes(method)) {{
                    console.debug('Sending PATCH/POST request with data:', JSON.stringify(data));
                    xhr.send(JSON.stringify(data));
                }} else {{
                    console.debug('Sending GET/DELETE request');
                    xhr.send();
                }}
            }});
        }}
        """
        # Wrap the Javascript function definition in an IIFE
        js_function_iife = f"""
        (function() {{
            window.{random_fn_name} = {js_function};
        }})();
        """
        self.log.debug(f"Generated global JS function {random_fn_name}: {js_function_iife}")
        self.page.evaluate(js_function_iife)

        js_script = f'(async () => {{ return await window.{random_fn_name}("{method}", "{url}", {json.dumps(query_params)}, {json.dumps(data)}, {json.dumps(headers)}, {timeout if timeout is not None else "null"}); }})()'
        self.log.debug(f"Generated script to execute global JS function {random_fn_name}: {js_script}")
        result = self.page.evaluate(js_script)

        js_script = f'delete window.{random_fn_name}'
        self.log.debug(f"Generated script to delete global JS function {random_fn_name}: {js_script}")
        self.page.evaluate(js_script)

        return result

    def _api_get_request(self, url, query_params=None, custom_headers=None, timeout=None):
        query_params = query_params or {}
        custom_headers = custom_headers or {}
        headers = self._api_request_build_headers(custom_headers)
        kwargs = {
            "headers": headers,
            "query_params": query_params,
        }
        if timeout:
            kwargs["timeout"] = timeout
        self.log.debug(f"GET {url} request, query params: {query_params}, headers: {headers}")
        response = self._api_xhr_request('GET', url, **kwargs)
        return self._process_api_response(url, response)

    def _api_post_request(self, url, data=None, custom_headers=None, timeout=None):
        data = data or {}
        custom_headers = custom_headers or {}
        headers = self._api_request_build_headers(custom_headers)
        kwargs = {
            "headers": headers,
            "data": data,
        }
        if timeout:
            kwargs["timeout"] = timeout
        self.log.debug(f"POST {url} request, data: {data}, headers: {headers}")
        response = self._api_xhr_request('POST', url, **kwargs)
        return self._process_api_response(url, response, method="POST")

    def _api_patch_request(self, url, data=None, custom_headers=None, timeout=None):
        data = data or {}
        custom_headers = custom_headers or {}
        headers = self._api_request_build_headers(custom_headers)
        kwargs = {
            "headers": headers,
            "data": data,
        }
        if timeout:
            kwargs["timeout"] = timeout
        self.log.debug(f"PATCH {url} request, data: {data}, headers: {headers}")
        response = self._api_xhr_request('PATCH', url, **kwargs)
        return self._process_api_response(url, response, method="PATCH")

    def _gen_title(self):
        if not self.conversation_id or self.conversation_id and self.conversation_title_set:
            return
        url = f"https://chat.openai.com/backend-api/conversation/gen_title/{self.conversation_id}"
        data = {
            "message_id": self.parent_message_id,
            "model": "text-davinci-002-render-sha",
        }
        ok = False
        try:
            ok, json, response = self._api_post_request(url, data, timeout=GEN_TITLE_TIMEOUT)
        except Exception as e:
            self.log.warning(f"Failed to generate title: {e}")
        if ok:
            # TODO: Do we want to do anything with the title we got back?
            # response_data = response.json()
            self.conversation_title_set = True
        else:
            self.log.warning("Failed to auto-generate title for new conversation")

    def conversation_data_to_messages(self, conversation_data):
        mapping_dict = conversation_data['messages'].values()
        messages = []
        parent_nodes = [item for item in mapping_dict if 'parent' not in item]
        mapping_dict = [item for item in mapping_dict if 'parent' in item]
        if len(parent_nodes) == 1 and 'children' in parent_nodes[0]:
            parent_id = parent_nodes[0]['children'][0]
        else:
            parent_id = None
        while True:
            current_item = next((item for item in mapping_dict if item['parent'] == parent_id), None)
            if current_item is None:
                return messages
            message = current_item['message']
            if message is not None and 'content' in message and 'author' in message and message['author']['role'] != 'system':
                message_content = ""
                if 'parts' in message['content']:
                    message_content = "".join(message['content']['parts'])
                elif 'result' in message['content']:
                    message_content = message['content']['result']
                messages.append({
                    'id': message['id'],
                    'role': message['author']['role'],
                    'message': message_content,
                    'created_time': datetime.datetime.fromtimestamp(int(message['create_time'])),
                })
            parent_id = current_item['id']

    def get_plugins(self):
        if self.session is None:
            self.refresh_session()
        query_params = {
            "offset": 0,
            "limit": 250,
            "statuses": "approved",
        }
        success, data, user_message = self._api_get_request("https://chat.openai.com/backend-api/aip/p", query_params=query_params)
        if success:
            return success, data['items'], user_message
        return success, data, user_message

    def enable_plugin(self, plugin_id):
        self.plugin_ids.append(plugin_id)
        self.plugin_ids = list(set(self.plugin_ids))
        return True, self.plugin_ids, f"Enabled plugin {plugin_id}"

    def disable_plugin(self, plugin_id):
        self.plugin_ids.remove(plugin_id)
        return True, self.plugin_ids, f"Disabled plugin {plugin_id}"

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
            return ok, json, response
        else:
            return self._handle_error(json, response, "Failed to delete conversation")

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
            return ok, json, "Title set"
        else:
            return self._handle_error(json, response, "Failed to set title")

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
                create_time = item['create_time'].split('.')[0]
                item['created_time'] = datetime.datetime.strptime(create_time, "%Y-%m-%dT%H:%M:%S")
                del item['create_time']
                history[item["id"]] = item
            return ok, history, "Retrieved history"
        else:
            return self._handle_error(json, response, "Failed to get history")

    def get_conversation(self, uuid=None):
        if self.session is None:
            self.refresh_session()
        uuid = uuid if uuid else self.conversation_id
        if uuid:
            url = f"https://chat.openai.com/backend-api/conversation/{uuid}"
            ok, json, response = self._api_get_request(url)
            if ok:
                conversation_data = {
                    'conversation': {
                        'id': uuid,
                        'title': json['title'],
                        'created_time': datetime.datetime.fromtimestamp(int(json['create_time'])),
                        'update_time': datetime.datetime.fromtimestamp(int(json['update_time'])),
                        'current_node': json['current_node'],
                    },
                    'messages': json['mapping'],
                }
                return ok, conversation_data, response
            else:
                return self._handle_error(json, response, f"Failed to get conversation {uuid}")

    def _ask_stream(self, prompt, title=None, request_overrides=None):
        request_overrides = request_overrides or {}
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
            "model": self.model,
            "conversation_id": self.conversation_id,
            "parent_message_id": self.parent_message_id,
            "action": "next",
        }
        models = self.provider.get_capability('models', {})
        if self.plugin_ids and self.model in models and models[self.model].get('plugins', False):
            self.log.debug(f"Using plugins: {self.plugin_ids}")
            request['plugin_ids'] = self.plugin_ids

        code = (
            """
            const stream_div = document.createElement('DIV');
            stream_div.id = "STREAM_DIV_ID";
            document.body.appendChild(stream_div);
            console.log(`STREAM_DIV_ID: ${stream_div.id}`);
            const xhr = new XMLHttpRequest();
            const url = "https://chat.openai.com/backend-api/conversation";
            xhr.open('POST', url);
            xhr.setRequestHeader('Accept', 'text/event-stream');
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Authorization', 'Bearer BEARER_TOKEN');
            xhr.responseType = 'stream';
            console.log(`Opened XHR streaming request to ${url}`);
            xhr.onreadystatechange = function() {
              console.debug(`XHR state change: readyState: ${xhr.readyState}`);
              var newEvent;
              const interrupt_div = document.getElementById('INTERRUPT_DIV_ID');
              if(xhr.readyState == 3 || xhr.readyState == 4) {
                const newData = xhr.response.substr(xhr.seenBytes);
                console.log(`Got new data: ${newData}`);
                try {
                  const newEvents = newData.split(/\\n\\n/).reverse();
                  newEvents.shift();
                  if(newEvents[0] == "data: [DONE]") {
                    console.log('Got done event');
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
                console.log(`Adding EOF_DIV_ID: ${eof_div.id}`);
                document.body.appendChild(eof_div);
              }
              if(typeof interrupt_div !== 'undefined' && interrupt_div !== null) {
                console.warn('Interrupting stream');
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

        self.log.debug(f"Sending stream request -- model: {self.model}, conversation_id: {self.conversation_id}, parent_message_id: {self.parent_message_id}")
        self.streaming = True
        self.page.evaluate(code)

        last_event_msg = ""
        last_tool_event_msg = ""
        current_message_type = ""
        last_message_type = ""
        start_time = time.time()
        while True:
            if not self.streaming:
                self.log.info("Request to interrupt streaming")
                self.interrupt_stream()
                break
            eof_datas = self.page.query_selector_all(f"div#{self.eof_div_id}")

            conversation_datas = self.page.query_selector_all(
                f"div#{self.stream_div_id}"
            )
            if len(conversation_datas) == 0:
                continue

            full_event_message = None
            tool_event_message = None

            try:
                event_raw = base64.b64decode(conversation_datas[0].inner_html())
                if len(event_raw) > 0:
                    event = json.loads(event_raw)
                    if event is not None and "message" in event:
                        # util.debug.console(event["message"])
                        self.parent_message_id = event["message"]["id"]
                        self.conversation_id = event["conversation_id"]
                        if "content" in event["message"]:
                            if "parts" in event["message"]["content"]:
                                full_event_message = "\n".join(
                                    event["message"]["content"]["parts"]
                                )
                                current_message_type = "message"
                            # Using a tool.
                            elif event["message"]["content"]["content_type"] == "code":
                                tool_event_message = event["message"]["content"]["text"]
                                current_message_type = "tool"
            except Exception:
                try:
                    self.log.error(f"Got bad event event: {event_raw}")
                except Exception:
                    self.log.error("Unknown streaming error")
                yield (
                    "Failed to read response from ChatGPT.  Tips:\n"
                    " * Try again.  ChatGPT can be flaky.\n"
                    " * Use the `session` command to refresh your session, and then try again.\n"
                    " * Restart the program in the `install` mode and make sure you are logged in."
                )
                break

            if last_message_type and last_message_type != current_message_type:
                yield "\n\n"
            if full_event_message is not None:
                chunk = full_event_message[len(last_event_msg):]
                self.message_clipboard = last_event_msg = full_event_message
                last_message_type = "message"
                yield chunk
            elif tool_event_message is not None:
                chunk = tool_event_message[len(last_tool_event_msg):]
                last_tool_event_msg = tool_event_message
                last_message_type = "tool"
                yield chunk

            # if we saw the eof signal, this was the last event we
            # should process and we are done
            if len(eof_datas) > 0 or (((time.time() - start_time) > self.timeout) and full_event_message is None):
                break

            time.sleep(0.2)

        if not self.streaming:
            yield (
                "\nGeneration stopped\n"
            )
        self.streaming = False
        self._cleanup_divs()
        if title:
            self.set_title(title)
        else:
            self._gen_title()

    def interrupt_stream(self):
        self.log.info("Interrupting stream")
        util.print_status_message(False, "\n\nWARNING:\nStream interruption on the browser backend is not currently working properly, and may require force closing the process.\nIf you'd like to help fix this error, see https://github.com/mmabrouk/chatgpt-wrapper/issues/274")
        code = (
            """
            const interrupt_div = document.createElement('DIV');
            interrupt_div.id = "INTERRUPT_DIV_ID";
            document.body.appendChild(interrupt_div);
            """
        ).replace("INTERRUPT_DIV_ID", self.interrupt_div_id)
        self.page.evaluate(code)

    def ask(self, message, title=None, request_overrides=None):
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        request_overrides = request_overrides or {}
        customizations = self.provider.get_customizations()
        llm = self.override_llm or self.make_llm(customizations)
        try:
            response = llm([HumanMessage(content=message)])
        except ValueError as e:
            return False, message, e
        return True, response.content, "Response received"

    def ask_stream(self, message, title=None, request_overrides=None):
        """
        Send a message to chatGPT and stream the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from OpenAI.
        """
        request_overrides = request_overrides or {}
        customizations = self.provider.get_customizations()
        customizations.update(self.streaming_args(interrupt_handler=True))
        llm = self.override_llm or self.make_llm(customizations)
        try:
            response = llm([HumanMessage(content=message)])
        except ValueError as e:
            return False, message, e
        return True, response.content, "Response received"

    def new_conversation(self):
        super().new_conversation()
        self.parent_message_id = str(uuid.uuid4())
