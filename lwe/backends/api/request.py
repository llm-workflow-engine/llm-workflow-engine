import copy

from langchain_community.adapters.openai import convert_message_to_dict
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage

from lwe.core.logger import Logger

from lwe.core import constants
import lwe.core.util as util
from lwe.core.tool_cache import ToolCache
from lwe.core.token_manager import TokenManager

from lwe.backends.api.orm import Orm
from lwe.backends.api.message import MessageManager


class ApiRequest:
    """Individual LLM requests manager"""

    def __init__(
        self,
        config=None,
        provider=None,
        provider_manager=None,
        tool_manager=None,
        input=None,
        preset=None,
        preset_manager=None,
        system_message=None,
        old_messages=None,
        max_submission_tokens=None,
        request_overrides=None,
        return_only=False,
        orm=None,
    ):
        self.config = config
        self.log = Logger(self.__class__.__name__, self.config)
        self.default_provider = provider
        self.provider = self.default_provider
        self.provider_manager = provider_manager
        self.tool_manager = tool_manager
        self.input = input
        self.default_preset = preset
        self.default_preset_name = util.get_preset_name(self.default_preset)
        self.preset_manager = preset_manager
        self.system_message = system_message or constants.SYSTEM_MESSAGE_DEFAULT
        self.old_messages = old_messages or []
        self.max_submission_tokens = (
            max_submission_tokens or constants.OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS
        )
        self.request_overrides = request_overrides or {}
        self.return_only = return_only
        self.orm = orm or Orm(self.config)
        self.message = MessageManager(config, self.orm)
        self.streaming = False
        self.log.debug(
            f"Inintialized ApiRequest with input: {self.input}, default preset name: {self.default_preset_name}, system_message: {self.system_message}, max_submission_tokens: {self.max_submission_tokens}, request_overrides: {self.request_overrides}, return only: {self.return_only}"
        )

    def set_request_llm(self):
        success, response, user_message = self.extract_metadata_customizations()
        if not success:
            return success, response, user_message
        preset_name, preset_overrides, metadata, customizations = response
        success, response, user_message = self.setup_request_config(
            preset_name, preset_overrides, metadata, customizations
        )
        return success, response, user_message

    def setup_request_config(
        self, preset_name=None, preset_overrides=None, metadata=None, customizations=None
    ):
        """
        Set up the configuration for the request.

        :param preset_name: Override preset name
        :type preset_name: str, optional
        :param preset_overrides: Overrides for preset, defaults to None
        :type preset_overrides: dict, optional
        :param metadata: Preset metadata
        :type metadata: dict, optional
        :param customizations: Provider/model customizations
        :type customizations: dict, optional
        :returns: success, llm, message
        :rtype: tuple
        """
        config = {
            "preset_name": preset_name,
            "preset_overrides": preset_overrides,
            "metadata": metadata,
            "customizations": customizations,
        }
        success, response, user_message = self.build_request_config(config)
        if success:
            provider, preset, llm, preset_name, model_name, token_manager = response
            self.llm = llm
            self.provider = provider
            self.token_manager = token_manager
            self.preset_name = preset_name
            self.model_name = model_name
            self.preset = preset
        return success, response, user_message

    def build_request_config(self, config):
        config = self.prepare_config(config)
        success, provider, user_message = self.load_provider(config)
        if not success:
            return success, provider, user_message
        config = self.merge_preset_overrides(config)
        preset = (config["metadata"], config["customizations"])
        customizations, tools, tool_choice = self.expand_tools(config["customizations"])
        config["customizations"] = customizations
        llm = provider.make_llm(
            config["customizations"], tools=tools, tool_choice=tool_choice, use_defaults=True
        )
        preset_name = config["metadata"].get("name", "")
        model_name = getattr(llm, provider.model_property_name)
        token_manager = TokenManager(self.config, provider, model_name, self.tool_cache)
        message = f"Built LLM based on preset_name: {preset_name or 'None'}, metadata: {config['metadata']}, customizations: {config['customizations']}, preset_overrides: {config['preset_overrides']}"
        self.log.debug(message)
        return True, (provider, preset, llm, preset_name, model_name, token_manager), message

    def prepare_config(self, config):
        config["metadata"] = copy.deepcopy(config["metadata"] or {})
        config["customizations"] = copy.deepcopy(config["customizations"] or {})
        config["preset_overrides"] = config["preset_overrides"] or {}
        return config

    def load_provider(self, config):
        if "provider" in config["metadata"]:
            return self.provider_manager.load_provider(config["metadata"]["provider"])
        return True, self.provider, "Default provider loaded"

    def merge_preset_overrides(self, config):
        if config["preset_overrides"]:
            if "metadata" in config["preset_overrides"]:
                self.log.info(
                    f"Merging preset overrides for metadata: {config['preset_overrides']['metadata']}"
                )
                config["metadata"] = util.merge_dicts(
                    config["metadata"], config["preset_overrides"]["metadata"]
                )
            if "model_customizations" in config["preset_overrides"]:
                self.log.info(
                    f"Merging preset overrides for model customizations: {config['preset_overrides']['model_customizations']}"
                )
                config["customizations"] = util.merge_dicts(
                    config["customizations"], config["preset_overrides"]["model_customizations"]
                )
        return config

    def extract_metadata_customizations(self):
        self.log.debug(
            f"Extracting preset configuration from request_overrides: {self.request_overrides}"
        )
        success, response, user_message = util.extract_preset_configuration_from_request_overrides(
            self.request_overrides, self.default_preset_name
        )
        if not success:
            return success, response, user_message
        preset_name, preset_overrides, _activate_preset = response
        metadata = {}
        customizations = {}
        if preset_name:
            self.log.debug(f"Preset {preset_name!r} extracted from request overrides")
            success, response, user_message = self.get_preset_metadata_customizations(preset_name)
            if success:
                metadata, customizations = response
            else:
                return success, response, user_message
        else:
            if self.default_preset:
                self.log.debug("Using default preset")
                metadata, _ = self.default_preset
            else:
                self.log.debug("Using current provider")
                metadata["provider"] = self.provider.name
            customizations = self.provider.get_customizations()
        return (
            success,
            (preset_name, preset_overrides, metadata, customizations),
            "Extracted metadata and customizations",
        )

    def get_preset_metadata_customizations(self, preset_name):
        success, preset, user_message = self.preset_manager.ensure_preset(preset_name)
        if not success:
            return success, preset, user_message
        metadata, customizations = preset
        self.log.debug(
            f"Retrieved metadata and customizations for preset: {preset_name}, metadata: {metadata}, customizations: {customizations}"
        )
        return (
            success,
            (metadata, customizations),
            f"Retrieved metadata and customizations for preset: {preset_name}",
        )

    def expand_tools(self, customizations):
        """Expand any configured tools to their full definition.

        :param customizations: Model customizations
        :type customizations: dict
        :returns: customizations, tools, tool_choice
        :rtype: tuple
        """
        customizations = copy.deepcopy(customizations)
        self.tool_cache = ToolCache(self.config, self.tool_manager, customizations)
        self.tool_cache.add_message_tools(self.old_messages)
        tools = [
            self.tool_manager.get_tool_config(tool_name) for tool_name in self.tool_cache.tools
        ]
        if "tools" in customizations:
            del customizations["tools"]
        tool_choice = customizations.pop("tool_choice", None)
        return customizations, tools, tool_choice

    def prepare_default_new_conversation_messages(self):
        """
        Prepare default new conversation messages.

        :returns: List of new messages
        :rtype: list
        """
        new_messages = []
        if len(self.old_messages) == 0:
            new_messages.append(
                self.message.build_message(
                    "system", self.request_overrides.get("system_message") or self.system_message
                )
            )
        new_messages.append(self.message.build_message("user", self.input))
        return new_messages

    def prepare_custom_new_conversation_messages(self):
        """
        Prepare custom new conversation messages.

        :returns: List of new messages
        :rtype: list
        """
        return [
            self.message.build_message(message["role"], message["content"])
            for message in self.input
        ]

    def prepare_new_conversation_messages(self):
        """
        Prepare new conversation messages.

        :returns: List of new messages
        :rtype: list
        """
        return (
            self.prepare_custom_new_conversation_messages()
            if type(self.input) is list
            else self.prepare_default_new_conversation_messages()
        )

    def prepare_ask_request(self):
        """
        Prepare the request for the LLM.

        :returns: New messages, messages
        :rtype: tuple
        """
        new_messages = self.prepare_new_conversation_messages()
        old_messages = self.tool_cache.add_message_tools(self.old_messages)
        messages = old_messages + new_messages
        messages = self.strip_out_messages_over_max_tokens(messages, self.max_submission_tokens)
        return new_messages, messages

    def strip_out_messages_over_max_tokens(self, messages, max_tokens):
        """
        Recursively strip out messages over max tokens.

        :param messages: Messages
        :type messages: list
        :param max_tokens: Max tokens
        :type max_tokens: int
        :returns: Messages
        :rtype: list
        """
        messages = copy.deepcopy(messages)
        token_count = self.token_manager.get_num_tokens_from_messages(messages)
        self.log.debug(
            f"Stripping messages over max tokens: {max_tokens}, initial token count: {token_count}"
        )
        stripped_messages_count = 0
        while token_count > max_tokens and len(messages) > 1:
            message = messages.pop(0)
            token_count = self.token_manager.get_num_tokens_from_messages(messages)
            self.log.debug(
                f"Stripping message: {message['role']}, {message['message']} -- new token count: {token_count}"
            )
            stripped_messages_count += 1
        token_count = self.token_manager.get_num_tokens_from_messages(messages)
        if token_count > max_tokens:
            raise Exception(
                f"No messages to send, all messages have been stripped, still over max submission tokens: {max_tokens}"
            )
        if stripped_messages_count > 0:
            max_tokens_exceeded_warning = f"Conversation exceeded max submission tokens ({max_tokens}), stripped out {stripped_messages_count} oldest messages before sending, sent {token_count} tokens instead"
            self.log.warning(max_tokens_exceeded_warning)
            util.print_status_message(False, max_tokens_exceeded_warning)
        return messages

    # TODO: Remove this when o1 models support system messages.
    def is_openai_o_series(self):
        if self.provider.name == "provider_chat_openai":
            model_name = getattr(self.llm, self.provider.model_property_name)
            if model_name.startswith("o1") or model_name.startswith("o3") or model_name.startswith("o4"):
                return True
        return False

    def is_openai_responses_api_series(self):
        if self.provider.name == "provider_chat_openai":
            model_name = getattr(self.llm, self.provider.model_property_name)
            if model_name.startswith("o1-pro") or model_name.startswith("o3-pro"):
                return True
        return False

    def is_openai_legacy_reasoning_model(self):
        if self.provider.name == "provider_chat_openai":
            model_name = getattr(self.llm, self.provider.model_property_name)
            if model_name.startswith("o1-mini") or model_name.startswith("o1-preview"):
                return True
        return False

    def call_llm(self, messages):
        """
        Call the LLM.

        :param messages: Messages
        :type messages: list
        :returns: success, response, message
        :rtype: tuple
        """
        stream = self.request_overrides.get("stream", False)
        self.log.debug(f"Calling LLM with message count: {len(messages)}")
        # TODO: Remove this when o1 models support system messages.
        if self.is_openai_o_series():
            if self.is_openai_responses_api_series():
                self.llm.use_responses_api = True
            if self.is_openai_legacy_reasoning_model():
                messages = [{**m, "role": "user"} if m["role"] == "system" else m for m in messages]
            self.llm.temperature = 1
        messages = self.build_chat_request(messages)
        if stream:
            return self.execute_llm_streaming(messages)
        else:
            return self.execute_llm_non_streaming(messages)

    def build_chat_request(self, messages):
        """
        Build chat request for LLM.

        :param messages: Messages
        :type messages: list
        :returns: Prepared messages
        :rtype: list
        """
        self.log.debug(f"Building messages for LLM, message count: {len(messages)}")
        messages = util.transform_messages_to_chat_messages(messages)
        messages = self.provider.prepare_messages_for_llm(messages)
        messages = self.attach_files(messages)
        return messages

    def attach_files(self, messages):
        files = self.request_overrides.get("files", [])
        if files:
            for file in files:
                file_data = self.provider.prepare_file_for_llm(file)
                messages.append(file_data)
        return messages

    def output_chunk_content(self, content, print_stream, stream_callback):
        if content:
            if print_stream:
                print(content, end="", flush=True)
            if stream_callback:
                stream_callback(content)

    def iterate_streaming_response(self, messages, print_stream, stream_callback):
        response = None
        previous_chunks = []
        self.log.debug(f"Streaming with LLM attributes: {self.llm.dict()}")
        provider_streaming_method = getattr(self.provider, "handle_streaming_chunk", None)
        for chunk in self.llm.stream(messages):
            if provider_streaming_method:
                content = provider_streaming_method(chunk, previous_chunks)
                response = content if not response else response + content
            elif isinstance(chunk, AIMessageChunk) or isinstance(chunk, AIMessage):
                content = chunk.content
                response = chunk if not response else response + chunk
            elif isinstance(chunk, str):
                content = chunk
                response = content if not response else response + content
            else:
                raise ValueError(f"Unexpected chunk type: {type(chunk)}")
            self.output_chunk_content(content, print_stream, stream_callback)
            if not self.streaming:
                if getattr(response, "tool_call_chunks", None):
                    response = None
                util.print_status_message(False, "Generation stopped")
                break
            previous_chunks.append(chunk)
        return response

    def execute_llm_streaming(self, messages):
        self.log.debug(f"Started streaming request at {util.current_datetime().isoformat()}")
        response = ""
        print_stream = self.request_overrides.get("print_stream", False)
        stream_callback = self.request_overrides.get("stream_callback", None)
        # Start streaming loop.
        self.streaming = True
        try:
            response = self.iterate_streaming_response(messages, print_stream, stream_callback)
        except ValueError as e:
            return False, messages, e
        finally:
            # End streaming loop.
            self.streaming = False
        self.log.debug(f"Stopped streaming response at {util.current_datetime().isoformat()}")
        return True, response, "Response received"

    def execute_llm_non_streaming(self, messages):
        self.log.info("Starting non-streaming request")
        self.log.debug(f"Non-streaming with LLM attributes: {self.llm.dict()}")
        provider_non_streaming_method = getattr(self.provider, "handle_non_streaming_response", None)
        try:
            response = self.llm.invoke(messages)
            if provider_non_streaming_method:
                response = provider_non_streaming_method(response)
        except ValueError as e:
            return False, messages, e
        return True, response, "Response received"

    def post_response(self, response_obj, new_messages):
        response_message, tool_calls = self.extract_message_content(response_obj)
        new_messages.append(response_message)

        if tool_calls:
            return self.handle_tool_calls(tool_calls, new_messages)

        return self.handle_non_tool_response(response_message, new_messages)

    def handle_tool_calls(self, tool_calls, new_messages):
        for tool_call in tool_calls:
            self.log_tool_call(tool_call)

        if self.should_return_on_tool_call():
            names = [tool_call["name"] for tool_call in tool_calls]
            self.log.info(f"Returning directly on tool call: {names}")
            return tool_calls, new_messages

        return self.execute_tool_calls(tool_calls, new_messages)

    def handle_non_tool_response(self, response_message, new_messages):
        tool_response, new_messages = self.check_return_on_tool_response(new_messages)
        if tool_response:
            self.log.info("Returning directly on tool response")
            return tool_response, new_messages

        return response_message["message"], new_messages

    def log_tool_call(self, tool_call):
        if not self.return_only:
            util.print_markdown(
                f"### AI requested tool call:\n* Name: {tool_call['name']}\n* Arguments: {tool_call['args']}"
            )

    def execute_tool_call(self, tool_call):
        success, tool_response, user_message = self.run_tool(tool_call["name"], tool_call["args"])
        if not success:
            raise ValueError(f"Tool call failed: {user_message}")
        return tool_response

    def execute_tool_calls(self, tool_calls, new_messages):
        for tool_call in tool_calls:
            tool_response = self.execute_tool_call(tool_call)
            new_messages.append(self.build_tool_response_message(tool_call, tool_response))

        # If a tool call is forced, we cannot recurse, as there will
        # never be a final non-tool response, and we'll recurse infinitely.
        # TODO: Perhaps in the future we can handle this more elegantly by:
        # 1. Tracking which tools with which arguments are called, and breaking
        #    on the first duplicate call.
        # 2. Allowing a 'maximum_forced_tool_calls' metadata attribute.
        # 3. Automatically switching the preset's 'tool_choice' to 'auto' after
        #    the first call.
        if self.check_forced_tool():
            self.log.debug("Returning directly on forced tool call")
            return tool_response, new_messages

        success, response_obj, user_message = self.call_llm(new_messages)
        if not success:
            raise ValueError(f"LLM call failed: {user_message}")

        return self.post_response(response_obj, new_messages)

    def build_tool_response_message(self, tool_call, tool_response):
        message_metadata = {
            "name": tool_call["name"],
        }
        if "id" in tool_call:
            message_metadata["id"] = tool_call["id"]
        return self.message.build_message(
            "tool",
            tool_response,
            message_type="tool_response",
            message_metadata=message_metadata,
        )

    def extract_message_content(self, message):
        """
        Extract the content from an LLM message.

        :param message: Message
        :type message: dict | BaseMessage
        :returns: Built message, tool calls
        :rtype: tuple
        """
        tool_calls = []
        if isinstance(message, BaseMessage):
            tool_calls = message.tool_calls
            invalid_tool_calls = getattr(message, "invalid_tool_calls", [])
            if invalid_tool_calls:
                tool_call_errors = ", ".join(
                    [
                        f"{tool_call['name']}: {tool_call['error']}"
                        for tool_call in invalid_tool_calls
                    ]
                )
                raise RuntimeError(f"LLM tool call failed: {tool_call_errors}")
            message_dict = convert_message_to_dict(message)
            content = message_dict["content"]
            message_type = "content"
            if tool_calls:
                message_type = "tool_call"
                content = tool_calls
            return (
                self.message.build_message(message_dict["role"], content, message_type),
                tool_calls,
            )
        return self.message.build_message("assistant", message), tool_calls

    def should_return_on_tool_call(self):
        """
        Check if should return on tool call.

        :returns: Whether to return on tool call
        :rtype: bool
        """
        metadata, _customizations = self.preset
        return "return_on_tool_call" in metadata and metadata["return_on_tool_call"]

    def check_forced_tool(self):
        """Check if a tool call is forced.

        :returns: True if forced tool
        :rtype: bool
        """
        _metadata, customizations = self.preset
        if "tool_choice" in customizations:
            return not (
                isinstance(customizations["tool_choice"], str)
                and customizations["tool_choice"] in ["auto", "none"]
            )
        return False

    def check_return_on_tool_response(self, new_messages):
        """
        Check for return on tool response.

        Supports multiple tool calls.

        :param new_messages: List of new messages
        :type new_messages: list
        :returns: Tool response or None, updated messages
        :rtype: tuple
        """
        metadata, _customizations = self.preset
        if "return_on_tool_response" in metadata and metadata["return_on_tool_response"]:
            # NOTE: In order to allow for multiple tool calling and
            # returning on the LAST tool response, we need to allow
            # the LLM to respond to all previous tool responses, as
            # it may respond with another tool call.
            #
            # Thus, at the end of all responses from the LLM, the last
            # message will be a natural language reponse, and the previous
            # message will be the last tool response.
            #
            # To correctly return the tool response and message list
            # we need to:
            # 1. Remove the last message
            # 2. Extract and return the tool response
            if self.is_tool_response_message(new_messages[-2]):
                new_messages.pop()
                tool_response = new_messages[-1]["message"]
                return tool_response, new_messages
        return None, new_messages

    def run_tool(self, tool_name, data):
        """Run a tool.

        :param tool_name: Tool name
        :type tool_name: str
        :param data: Tool arguments
        :type data: dict
        :returns: success, response, message
        :rtype: tuple
        """
        success, response, user_message = self.tool_manager.run_tool(tool_name, data)
        json_obj = response if success else {"error": user_message}
        if not self.return_only:
            util.print_markdown(f"### Tool response:\n* Name: {tool_name}\n* Success: {success}")
            util.print_markdown(json_obj)
        return success, json_obj, user_message

    def is_tool_response_message(self, message):
        """Check if a message is a tool response.

        :param message: The message
        :type message: dict
        :returns: True if tool response
        :rtype: bool
        """
        return message["message_type"] == "tool_response"

    def terminate_stream(self, _signal, _frame):
        """
        Handles termination signal and stops the stream if it's running.
        """
        self.log.info("Received signal to terminate stream")
        if self.streaming:
            self.streaming = False
