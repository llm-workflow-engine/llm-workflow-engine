import copy
import json

from langchain.schema.messages import (
    AIMessage,
    AIMessageChunk,
)

from lwe.core.logger import Logger

from lwe.core import constants
import lwe.core.util as util
from lwe.core.function_cache import FunctionCache
from lwe.core.token_manager import TokenManager

from lwe.backends.api.message import MessageManager

from langchain.schema import BaseMessage
from langchain.adapters.openai import convert_message_to_dict

class ApiRequest:
    """Individual LLM requests manager
    """

    def __init__(self,
                 config=None,
                 provider=None,
                 provider_manager=None,
                 function_manager=None,
                 input=None,
                 preset=None,
                 preset_manager=None,
                 system_message=constants.SYSTEM_MESSAGE_DEFAULT,
                 old_messages=None,
                 max_submission_tokens=constants.OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS,
                 request_overrides=None,
                 return_only=False,
                 ):
        self.config = config
        self.log = Logger(self.__class__.__name__, self.config)
        self.default_provider = provider
        self.provider = self.default_provider
        self.provider_manager = provider_manager
        self.function_manager = function_manager
        self.input = input
        self.default_preset = preset
        self.default_preset_name = util.get_preset_name(self.default_preset)
        self.preset_manager = preset_manager
        self.system_message = system_message
        self.old_messages = old_messages or []
        self.max_submission_tokens = max_submission_tokens
        self.request_overrides = request_overrides or {}
        self.return_only = return_only
        self.message = MessageManager(config)

    def set_request_llm(self):
        success, response, user_message = self.extract_metadata_customizations()
        if not success:
            return success, response, user_message
        preset_name, preset_overrides, metadata, customizations = response
        success, response, user_message = self.build_llm(preset_name, preset_overrides, metadata, customizations)
        return success, response, user_message

    def extract_metadata_customizations(self):
        self.log.debug(f"Extracting preset configuration from request_overrides: {self.request_overrides}")
        success, response, user_message = util.extract_preset_configuration_from_request_overrides(self.request_overrides, self.default_preset_name)
        if not success:
            return success, response, user_message
        preset_name, preset_overrides, _activate_preset = response
        metadata = {}
        customizations = {}
        if preset_name:
            self.log.debug(f"Preset '{preset_name}' extracted from request overrides")
            success, response, user_message = self.get_preset_metadata_customizations(preset_name)
            if success:
                metadata, customizations = response
            else:
                return success, response, user_message
        elif self.default_preset:
            self.log.debug("Using default preset")
            metadata, customizations = self.default_preset
        else:
            self.log.debug("Using current provider")
            metadata['provider'] = self.provider.name
            customizations = self.provider.get_customizations()
        return success, (preset_name, preset_overrides, metadata, customizations), "Extracted metadata and customizations"

    def get_preset_metadata_customizations(self, preset_name):
        success, preset, user_message = self.preset_manager.ensure_preset(preset_name)
        if not success:
            return success, preset, user_message
        metadata, customizations = preset
        self.log.debug(f"Retrieved metadata and customizations for preset: {preset_name}, metadata: {metadata}, customizations: {customizations}")
        return success, (metadata, customizations), f"Retrieved metadata and customizations for preset: {preset_name}"

    def build_llm(self, preset_name=None, preset_overrides=None, metadata=None, customizations=None):
        """
        Build the LLM object for the request.

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
        metadata = metadata or {}
        customizations = customizations or {}
        preset_overrides = preset_overrides or {}
        metadata = copy.deepcopy(metadata)
        customizations = copy.deepcopy(customizations)
        if preset_name is None:
            success, provider, user_message = self.provider_manager.load_provider(metadata['provider'])
            if success:
                self.provider = provider
            else:
                return success, provider, user_message
        if preset_overrides:
            if 'metadata' in preset_overrides:
                self.log.info(f"Merging preset overrides for metadata: {preset_overrides['metadata']}")
                metadata = util.merge_dicts(metadata, preset_overrides['metadata'])
            if 'model_customizations' in preset_overrides:
                self.log.info(f"Merging preset overrides for model customizations: {preset_overrides['model_customizations']}")
                customizations = util.merge_dicts(customizations, preset_overrides['model_customizations'])
        customizations = self.expand_functions(customizations)
        self.llm = self.provider.make_llm(customizations, use_defaults=True)
        self.preset = (metadata, customizations)
        self.preset_name = metadata.get('name', '')
        self.model_name = getattr(self.llm, self.provider.model_property_name)
        self.token_manager = TokenManager(self.config, self.provider, self.model_name, self.function_cache)
        message = f"Built LLM based on preset_name: {self.preset_name}, metadata: {metadata}, customizations: {customizations}, preset_overrides: {preset_overrides}"
        self.log.debug(message)
        return True, self.llm, message

    def expand_functions(self, customizations):
        """Expand any configured functions to their full definition."""
        self.function_cache = FunctionCache(self.config, self.function_manager, customizations)
        self.function_cache.add_message_functions(self.old_messages)
        already_configured_functions = []
        if 'model_kwargs' in customizations and 'functions' in customizations['model_kwargs']:
            for idx, function_name in enumerate(customizations['model_kwargs']['functions']):
                already_configured_functions.append(function_name)
                if isinstance(function_name, str):
                    customizations['model_kwargs']['functions'][idx] = self.function_manager.get_function_config(function_name)
        if len(self.function_cache.functions) > 0:
            customizations.setdefault('model_kwargs', {})
            customizations['model_kwargs'].setdefault('functions', [])
            for function_name in self.function_cache.functions:
                if function_name not in already_configured_functions:
                    customizations['model_kwargs']['functions'].append(self.function_manager.get_function_config(function_name))
        return customizations

    def prepare_new_conversation_messages(self):
        """
        Prepare new conversation messages.

        :returns: List of new messages
        :rtype: list
        """
        new_messages = []
        if len(self.old_messages) == 0:
            new_messages.append(self.message.build_message('system', self.request_overrides.get('system_message') or self.system_message))
        new_messages.append(self.message.build_message('user', self.input))
        return new_messages

    def prepare_ask_request(self):
        """
        Prepare the request for the LLM.

        :returns: New messages, messages
        :rtype: tuple
        """
        new_messages = self.prepare_new_conversation_messages()
        old_messages = self.function_cache.add_message_functions(self.old_messages)
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
        self.log.debug(f"Stripping messages over max tokens: {max_tokens}, initial token count: {token_count}")
        stripped_messages_count = 0
        while token_count > max_tokens and len(messages) > 1:
            message = messages.pop(0)
            token_count = self.token_manager.get_num_tokens_from_messages(messages)
            self.log.debug(f"Stripping message: {message['role']}, {message['message']} -- new token count: {token_count}")
            stripped_messages_count += 1
        token_count = self.token_manager.get_num_tokens_from_messages(messages)
        if token_count > max_tokens:
            raise Exception(f"No messages to send, all messages have been stripped, still over max submission tokens: {max_tokens}")
        if stripped_messages_count > 0:
            max_tokens_exceeded_warning = f"Conversation exceeded max submission tokens ({max_tokens}), stripped out {stripped_messages_count} oldest messages before sending, sent {token_count} tokens instead"
            self.log.warning(max_tokens_exceeded_warning)
            util.print_status_message(False, max_tokens_exceeded_warning)
        return messages

    def call_llm(self, messages):
        """
        Call the LLM.

        :param messages: Messages
        :type messages: list
        :returns: success, response, message
        :rtype: tuple
        """
        stream = self.request_overrides.get('stream', False)
        self.log.debug(f"Calling LLM with message count: {len(messages)}")
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
        return messages

    def iterate_streaming_response(self, messages, print_stream, stream_callback):
        response = None
        is_function_call = False
        for chunk in self.llm.stream(messages):
            if isinstance(chunk, AIMessageChunk):
                content = chunk.content
                function_call = chunk.additional_kwargs.get('function_call')
                if response:
                    response.content += content
                    if function_call:
                        response.additional_kwargs['function_call']['arguments'] += function_call['arguments']
                else:
                    response = AIMessage(**dict(chunk))
                    if function_call:
                        is_function_call = True
            elif isinstance(chunk, str):
                content = chunk
                response = content if not response else response + content
            else:
                raise ValueError(f"Unexpected chunk type: {type(chunk)}")
            if content:
                if print_stream:
                    print(content, end="", flush=True)
                if stream_callback:
                    stream_callback(content)
            if not self.streaming:
                if is_function_call:
                    response = None
                util.print_status_message(False, "Generation stopped")
                break
        return response

    def execute_llm_streaming(self, messages):
        self.log.debug(f"Started streaming request at {util.current_datetime().isoformat()}")
        response = ""
        print_stream = self.request_overrides.get('print_stream', False)
        stream_callback = self.request_overrides.get('stream_callback', None)
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
        try:
            response = self.llm(messages)
        except ValueError as e:
            return False, messages, e
        return True, response, "Response received"

    def post_response(self, response_obj, new_messages):
        """Post-process the model response.

        :param response_obj: Raw response object
        :param new_messages: Generated messages
        :type new_messages: list
        :param request_overrides: Request overrides
        :type request_overrides: dict
        :returns: Response, updated messages
        :rtype: tuple
        """
        response_message = self.extract_message_content(response_obj)
        new_messages.append(response_message)
        if response_message['message_type'] == 'function_call':
            function_call = response_message['message']
            if not self.return_only:
                util.print_markdown(f"### AI requested function call:\n* Name: {function_call['name']}\n* Arguments: {function_call['arguments']}")
            if self.should_return_on_function_call():
                function_definition = {
                    'name': function_call['name'],
                    'arguments': function_call['arguments'],
                }
                self.log.info(f"Returning directly on function call: {function_call['name']}")
                return function_definition, new_messages
            success, function_response, user_message = self.run_function(function_call['name'], function_call['arguments'])
            if success:
                message_metadata = {
                    'name': function_call['name'],
                }
                new_messages.append(self.message.build_message('function', function_response, message_type='function_response', message_metadata=message_metadata))
                # If a function call is forced, we cannot recurse, as there will
                # never be a final non-function response, and we'l recurse infinitely.
                # TODO: Perhaps in the future we can handle this more elegantly by:
                # 1. Tracking which functions with which arguments are called, and breaking
                #    on the first duplicate call.
                # 2. Allowing a 'maximum_forced_function_calls' metadata attribute.
                # 3. Automatically switching the preset's 'function_call' to 'auto' after
                #    the first call.
                if self.check_forced_function():
                    return function_response, new_messages
                success, response_obj, user_message = self.call_llm(new_messages)
                if success:
                    return self.post_response(response_obj, new_messages)
                else:
                    return user_message, new_messages
            else:
                return user_message, new_messages
        function_response, new_messages = self.check_return_on_function_response(new_messages)
        if function_response:
            self.log.info(f"Returning directly on function response: {function_call['name']}")
            return function_response, new_messages
        return response_message['message'], new_messages

    def extract_message_content(self, message):
        """
        Extract the content from an LLM message.

        :param message: Message
        :type message: dict
        :returns: Content
        :rtype: str
        """
        if isinstance(message, BaseMessage):
            message_dict = convert_message_to_dict(message)
            content = message_dict['content']
            message_type = 'content'
            if 'function_call' in message_dict:
                message_type = 'function_call'
                message_dict['function_call']['arguments'] = json.loads(message_dict['function_call']['arguments'], strict=False)
                content = message_dict['function_call']
            elif message_dict['role'] == 'function':
                message_type = 'function_response'
            return self.message.build_message(message_dict['role'], content, message_type)
        return self.message.build_message('assistant', message)

    def should_return_on_function_call(self):
        """
        Check if should return on function call.

        :returns: Whether to return on function call
        :rtype: bool
        """
        metadata, _customizations = self.preset
        return 'return_on_function_call' in metadata and metadata['return_on_function_call']

    def check_forced_function(self):
        """Check if a function call is forced.

        :returns: True if forced function
        :rtype: bool
        """
        _metadata, customizations = self.preset
        return 'model_kwargs' in customizations and 'function_call' in customizations['model_kwargs'] and isinstance(customizations['model_kwargs']['function_call'], dict)

    def check_return_on_function_response(self, new_messages):
        """
        Check for return on function response.

        Supports multiple function calls.

        :param new_messages: List of new messages
        :type new_messages: list
        :returns: Function response or None, updated messages
        :rtype: tuple
        """
        metadata, _customizations = self.preset
        if 'return_on_function_response' in metadata and metadata['return_on_function_response']:
            # NOTE: In order to allow for multiple function calling and
            # returning on the LAST function response, we need to allow
            # the LLM to respond to all previous function responses, as
            # it may respond with another function call.
            #
            # Thus, at the end of all responses from the LLM, the last
            # message will be a natural language reponse, and the previous
            # message will be the last function response.
            #
            # To correctly return the function response and message list
            # we need to:
            # 1. Remove the last message
            # 2. Extract and return the function response
            if self.is_function_response_message(new_messages[-2]):
                new_messages.pop()
                function_response = new_messages[-1]['message']
                return function_response, new_messages
        return None, new_messages

    def run_function(self, function_name, data):
        """Run a function.

        :param function_name: Function name
        :type function_name: str
        :param data: Function arguments
        :type data: dict
        :returns: success, response, message
        :rtype: tuple
        """
        success, response, user_message = self.function_manager.run_function(function_name, data)
        json_obj = response if success else {'error': user_message}
        if not self.return_only:
            util.print_markdown(f"### Function response:\n* Name: {function_name}\n* Success: {success}")
            util.print_markdown(json_obj)
        return success, json_obj, user_message

    def is_function_response_message(self, message):
        """Check if a message is a function response.

        :param message: The message
        :type message: dict
        :returns: True if function response
        :rtype: bool
        """
        return message['message_type'] == 'function_response'
