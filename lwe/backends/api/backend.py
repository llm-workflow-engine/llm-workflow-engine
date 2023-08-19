import json
import threading
import tiktoken

from langchain.chat_models.openai import ChatOpenAI
from langchain.chat_models import ChatLiteLLM
from langchain.schema import BaseMessage
from langchain.chat_models.openai import _convert_message_to_dict

from lwe.core.backend import Backend
from lwe.core.provider_manager import ProviderManager
from lwe.core.workflow_manager import WorkflowManager
from lwe.core.function_manager import FunctionManager
from lwe.core.plugin_manager import PluginManager
import lwe.core.constants as constants
import lwe.core.util as util
from lwe.backends.api.user import UserManager
from lwe.backends.api.conversation import ConversationManager
from lwe.backends.api.message import MessageManager
from lwe.core.preset_manager import parse_llm_dict

ADDITIONAL_PLUGINS = [
    'provider_chat_openai',
]

class ApiBackend(Backend):
    """Backend implementation using direct API access.
    """

    name = "api"

    def __init__(self, config=None):
        """
        Initializes the Backend instance.

        This method sets up attributes that should only be initialized once.

        :param config: Optional configuration for the backend. If not provided, it uses a default configuration.
        """
        super().__init__(config)
        self.current_user = None
        self.user_manager = UserManager(config)
        self.conversation = ConversationManager(config)
        self.message = MessageManager(config)
        self.initialize_backend(config)

    def initialize_backend(self, config=None):
        """
        Initializes the backend with provided or default configuration,
        and sets up necessary attributes.

        This method is safe to call for dynamically reloading backends.

        :param config: Backend configuration options
        :type config: dict, optional
        """
        super().initialize_backend(config)
        self.override_provider = None
        self.override_preset = None
        self.override_llm = None
        self.return_only = False
        self.plugin_manager = PluginManager(self.config, self, additional_plugins=ADDITIONAL_PLUGINS)
        self.provider_manager = ProviderManager(self.config, self.plugin_manager)
        self.workflow_manager = WorkflowManager(self.config)
        self.function_manager = FunctionManager(self.config)
        self.workflow_manager.load_workflows()
        self.init_provider()
        self.set_available_models()
        self.set_conversation_tokens(0)
        self.load_default_user()
        self.load_default_conversation()

    def load_default_user(self):
        default_user = self.config.get('backend_options.default_user')
        if default_user is not None:
            self.load_user(default_user)

    def load_default_conversation(self):
        default_conversation_id = self.config.get('backend_options.default_conversation_id')
        if default_conversation_id is not None:
            self.load_conversation(default_conversation_id)

    def load_user(self, identifier):
        """Load a user by id or username/email.

        :param identifier: User id or username/email
        :type identifier: int, str
        :raises Exception: If user not found
        """
        if isinstance(identifier, int):
            success, user, user_message = self.user_manager.get_by_user_id(identifier)
        else:
            success, user, user_message = self.user_manager.get_by_username_or_email(identifier)
        if not success or not user:
            raise Exception(user_message)
        self.set_current_user(user)

    def load_conversation(self, conversation_id):
        """
        Load a conversation by id.

        :param conversation_id: Conversation id
        :type conversation_id: int
        """
        success, conversation_data, user_message = self.get_conversation(conversation_id)
        if success:
            if conversation_data:
                self.switch_to_conversation(conversation_id)
                return
            else:
                user_message = "Missing conversation data"
        raise Exception(user_message)

    def init_system_message(self):
        """Initialize the system message from config."""
        success, _alias, user_message = self.set_system_message(self.config.get('model.default_system_message'))
        if not success:
            util.print_status_message(success, user_message)
            self.set_system_message()

    def get_providers(self):
        """Get available provider plugins."""
        return self.provider_manager.get_provider_plugins()

    def init_provider(self):
        """Initialize the default provider and model."""
        self.init_system_message()
        self.active_preset = None
        self.active_preset_name = None
        default_preset = self.config.get('model.default_preset')
        if default_preset:
            success, preset, user_message = self.activate_preset(default_preset)
            if success:
                return
            util.print_status_message(False, f"Failed to load default preset {default_preset}: {user_message}")
        self.set_provider('provider_chat_openai')

    def set_provider(self, provider_name, customizations=None, reset=False):
        """
        Set the active provider plugin.

        :param provider_name: Name of provider plugin
        :type provider_name: str
        :param customizations: Customizations for provider, defaults to None
        :type customizations: dict, optional
        :param reset: Whether to reset provider, defaults to False
        :type reset: bool, optional
        :returns: success, provider, message
        :rtype: tuple
        """
        self.log.debug(f"Setting provider to: {provider_name}, with customizations: {customizations}, reset: {reset}")
        self.active_preset = None
        self.active_preset_name = None
        provider_full_name = self.provider_manager.full_name(provider_name)
        if self.provider_name == provider_full_name and not reset:
            return False, None, f"Provider {provider_name} already set"
        success, provider, user_message = self.provider_manager.load_provider(provider_full_name)
        if success:
            provider.setup()
            self.provider_name = provider_full_name
            self.provider = provider
            if isinstance(customizations, dict):
                for key, value in customizations.items():
                    success, customizations, customization_message = self.provider.set_customization_value(key, value)
                    if not success:
                        return success, customizations, customization_message
            self.llm = self.make_llm()
            self.set_model(getattr(self.llm, self.provider.model_property_name))
        return success, provider, user_message

    # TODO: This feels hacky, perhaps better to have a shell register itself
    # for output from the backend?
    def set_return_only(self, return_only=False):
        self.return_only = return_only

    def set_model(self, model_name):
        """
        Set the active model.

        :param model_name: Name of model
        :type model_name: str
        :returns: success, customizations, message
        :rtype: tuple
        """
        self.log.debug(f"Setting model to: {model_name}")
        success, customizations, user_message = super().set_model(model_name)
        self.set_max_submission_tokens(force=True)
        return success, customizations, user_message

    def set_override_llm(self, preset_name=None, preset_overrides=None):
        """
        Set override LLM based on preset.

        :param preset_name: Name of preset, defaults to None
        :type preset_name: str, optional
        :param preset_overrides: Overrides for preset, defaults to None
        :type preset_overrides: dict, optional
        :returns: success, llm, message
        :rtype: tuple
        """
        if preset_name:
            self.log.info(f"Setting override LLM to preset: {preset_name}")
            success, preset, user_message = self.preset_manager.ensure_preset(preset_name)
            if success:
                metadata, customizations = preset
                if preset_overrides:
                    if 'metadata' in preset_overrides:
                        self.log.info(f"Merging preset overrides for metadata: {preset_overrides['metadata']}")
                        metadata = util.merge_dicts(metadata, preset_overrides['metadata'])
                    if 'model_customizations' in preset_overrides:
                        self.log.info(f"Merging preset overrides for model customizations: {preset_overrides['model_customizations']}")
                        customizations = util.merge_dicts(customizations, preset_overrides['model_customizations'])
                customizations = self.expand_functions(customizations)
                success, provider, user_message = self.provider_manager.load_provider(metadata['provider'])
                if success:
                    self.override_llm = provider.make_llm(customizations, use_defaults=True)
                    self.override_provider = provider
                    self.override_preset = preset
                    message = f"Set override LLM based on preset {preset_name}"
                    self.log.debug(message)
                    return True, self.override_llm, message
            return False, None, user_message
        else:
            self.log.debug("Unsetting override LLM")
            self.override_preset = None
            self.override_provider = None
            self.override_llm = None
            message = "Unset override LLM"
            self.log.debug(message)
            return True, None, message

    def init_function_cache(self):
        """Initialize the function cache."""
        success, _functions, user_message = self.function_manager.load_functions()
        if not success:
            raise RuntimeError(user_message)
        self.function_cache = []
        if self.active_preset:
            _metadata, customizations = self.active_preset
            if 'model_kwargs' in customizations and 'functions' in customizations['model_kwargs']:
                for function in customizations['model_kwargs']['functions']:
                    self.function_cache.append(function)

    def function_cache_add(self, function_name):
        """Add a function to the cache if valid."""
        if self.function_manager.is_langchain_tool(function_name):
            if not self.function_manager.get_langchain_tool(function_name):
                return False
        else:
            if function_name not in self.function_manager.functions:
                return False
        if function_name not in self.function_cache:
            self.function_cache.append(function_name)
        return True

    def add_message_functions_to_cache(self, messages):
        """Add any function calls in messages to cache."""
        filtered_messages = []
        for message in messages:
            m_type = message['message_type']
            if m_type in ['function_call', 'function_response']:
                if m_type == 'function_call':
                    function_name = message['message']['name']
                if m_type == 'function_response':
                    function_name = message['message_metadata']['name']
                if self.function_cache_add(function_name):
                    filtered_messages.append(message)
                else:
                    message = f"Function {function_name} not found in function list, filtered message out"
                    self.log.warning(message)
                    util.print_status_message(False, message)
            else:
                filtered_messages.append(message)
        return filtered_messages

    def expand_functions(self, customizations):
        """Expand any configured functions to their full definition."""
        self.init_function_cache()
        # Necessary to seed function cache.
        self.retrieve_old_messages(self.conversation_id)
        already_configured_functions = []
        if 'model_kwargs' in customizations and 'functions' in customizations['model_kwargs']:
            for idx, function_name in enumerate(customizations['model_kwargs']['functions']):
                already_configured_functions.append(function_name)
                if isinstance(function_name, str):
                    customizations['model_kwargs']['functions'][idx] = self.function_manager.get_function_config(function_name)
        if len(self.function_cache) > 0:
            customizations.setdefault('model_kwargs', {})
            customizations['model_kwargs'].setdefault('functions', [])
            for function_name in self.function_cache:
                if function_name not in already_configured_functions:
                    customizations['model_kwargs']['functions'].append(self.function_manager.get_function_config(function_name))
        return customizations

    def compact_functions(self, customizations):
        """Compact expanded functions to just their name."""
        if 'model_kwargs' in customizations and 'functions' in customizations['model_kwargs']:
            customizations['model_kwargs']['functions'] = [f['name'] for f in customizations['model_kwargs']['functions']]
        return customizations

    def make_preset(self):
        """Make preset from current provider customizations."""
        metadata, customizations = parse_llm_dict(self.provider.customizations)
        customizations = self.compact_functions(customizations)
        return metadata, customizations

    def activate_preset(self, preset_name):
        """
        Activate a preset.

        :param preset_name: Name of preset
        :type preset_name: str
        :returns: success, preset, message
        :rtype: tuple
        """
        self.log.debug(f"Activating preset: {preset_name}")
        success, preset, user_message = self.preset_manager.ensure_preset(preset_name)
        if not success:
            return success, preset, user_message
        metadata, customizations = preset
        success, provider, user_message = self.set_provider(metadata['provider'], customizations, reset=True)
        if success:
            self.active_preset = preset
            self.active_preset_name = preset_name
            if 'system_message' in metadata:
                self.set_system_message(metadata['system_message'])
        return success, preset, user_message

    def _handle_response(self, success, obj, message):
        """
        Handle response tuple.

        Logs errors if not successful.

        :param success: If request was successful
        :type success: bool
        :param obj: Returned object
        :param message: Message
        :type message: str
        :returns: success, obj, message
        :rtype: tuple
        """
        if not success:
            self.log.error(message)
        return success, obj, message

    def get_token_encoding(self, model="gpt-3.5-turbo"):
        """
        Get token encoding for a model.

        :param model: Model name, defaults to "gpt-3.5-turbo"
        :type model: str, optional
        :raises NotImplementedError: If unsupported model
        :raises Exception: If error getting encoding
        :returns: Encoding object
        :rtype: Encoding
        """
        if model not in self.available_models:
            raise NotImplementedError("Unsupported engine {self.engine}")
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            raise Exception(f"Unable to get token encoding for model {model}: {str(e)}")
        return encoding

    def get_num_tokens_from_messages(self, messages, encoding=None):
        """
        Get number of tokens for a list of messages.

        :param messages: List of messages
        :type messages: list
        :param encoding: Encoding to use, defaults to None to auto-detect
        :type encoding: Encoding, optional
        :returns: Number of tokens
        :rtype: int
        """
        if not encoding:
            encoding = self.get_token_encoding()
        num_tokens = 0
        self.init_function_cache()
        messages = self.add_message_functions_to_cache(messages)
        messages = self.transform_messages_to_chat_messages(messages)
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                if isinstance(value, dict):
                    value = json.dumps(value, indent=2)
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        if len(self.function_cache) > 0:
            functions = [self.function_manager.get_function_config(function_name) for function_name in self.function_cache]
            functions_string = json.dumps(functions, indent=2)
            num_tokens += len(encoding.encode(functions_string))
        return num_tokens

    def set_conversation_tokens(self, tokens):
        """
        Set current conversation token count.

        :param tokens: Number of conversation tokens
        :type tokens: int
        """
        if self.conversation_id is None:
            provider = self.provider
        else:
            success, last_message, user_message = self.message.get_last_message(self.conversation_id)
            if not success:
                raise ValueError(user_message)
            provider = self.provider_manager.get_provider_from_name(last_message['provider'])
        if provider is not None and provider.get_capability('chat'):
            self.conversation_tokens = tokens
        else:
            self.conversation_tokens = None

    def switch_to_conversation(self, conversation_id):
        """
        Switch to a conversation.

        :param conversation_id: Conversation id
        :type conversation_id: int
        """
        success, conversation, user_message = self.get_conversation(conversation_id)
        if success:
            self.conversation_id = conversation_id
            self.conversation_title = conversation['conversation']['title']
        else:
            raise ValueError(user_message)
        success, last_message, user_message = self.message.get_last_message(self.conversation_id)
        if not success:
            raise ValueError(user_message)
        model_configured = False
        if last_message['preset']:
            success, _preset, user_message = self.activate_preset(last_message['preset'])
            if success:
                model_configured = True
            else:
                util.print_status_message(False, f"Unable to switch conversation to previous preset '{last_message['preset']}' -- ERROR: {user_message}, falling back to provider: {last_message['provider']}, model: {last_message['model']}")
        if not model_configured:
            if last_message['provider'] and last_message['model']:
                success, _provider, _user_message = self.set_provider(last_message['provider'], reset=True)
                if success:
                    success, _customizations, _user_message = self.set_model(last_message['model'])
                    if success:
                        self.init_system_message()
                        model_configured = True
        if not model_configured:
            util.print_status_message(False, "Invalid conversation provider/model, falling back to default provider/model")
            self.init_provider()
        tokens = self.get_conversation_token_count(conversation_id)
        self.set_conversation_tokens(tokens)

    def get_conversation_token_count(self, conversation_id=None):
        """Get token count for a conversation.

        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :returns: Number of tokens
        :rtype: int
        """
        conversation_id = conversation_id or self.conversation_id
        success, old_messages, user_message = self.message.get_messages(conversation_id)
        if not success:
            raise Exception(user_message)
        tokens = self.get_num_tokens_from_messages(old_messages)
        return tokens

    def should_return_on_function_call(self):
        """
        Check if should return on function call.

        :returns: Whether to return on function call
        :rtype: bool
        """
        preset = self.override_preset or self.active_preset
        if preset:
            metadata, _customizations = preset
            if 'return_on_function_call' in metadata and metadata['return_on_function_call']:
                return True
        return False

    def is_function_response_message(self, message):
        """Check if a message is a function response.

        :param message: The message
        :type message: dict
        :returns: True if function response
        :rtype: bool
        """
        return message['message_type'] == 'function_response'

    def check_return_on_function_response(self, new_messages):
        """
        Check for return on function response.

        Supports multiple function calls.

        :param new_messages: List of new messages
        :type new_messages: list
        :returns: Function response or None, updated messages
        :rtype: tuple
        """
        preset = self.override_preset or self.active_preset
        if preset:
            metadata, _customizations = preset
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

    def check_forced_function(self):
        """Check if a function call is forced.

        :returns: True if forced function
        :rtype: bool
        """
        preset = self.override_preset or self.active_preset
        if preset:
            _metadata, customizations = preset
            if 'model_kwargs' in customizations and 'function_call' in customizations['model_kwargs'] and isinstance(customizations['model_kwargs']['function_call'], dict):
                return True
        return False

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

    def post_response(self, response_obj, new_messages, request_overrides):
        """Post-process the model response.

        :param response_obj: Raw response object
        :param new_messages: Generated messages
        :type new_messages: list
        :param request_overrides: Request overrides
        :type request_overrides: dict
        :returns: Response, updated messages
        :rtype: tuple
        """
        response_message = self._extract_message_content(response_obj)
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
                success, response_obj, user_message = self._call_llm(new_messages, request_overrides)
                if success:
                    return self.post_response(response_obj, new_messages, request_overrides)
                else:
                    return user_message, new_messages
            else:
                return user_message, new_messages
        function_response, new_messages = self.check_return_on_function_response(new_messages)
        if function_response:
            self.log.info(f"Returning directly on function response: {function_call['name']}")
            return function_response, new_messages
        return response_message['message'], new_messages

    def transform_messages_to_chat_messages(self, messages):
        """
        Transform messages to chat messages.

        :param messages: List of messages
        :type messages: list
        :returns: List of chat messages
        :rtype: list
        """
        chat_messages = []
        for message in messages:
            role = message['role']
            next_message = {
                'role': role,
            }
            if role == "assistant":
                if message['message_type'] == "function_call":
                    next_message['function_call'] = {
                        'name': message['message']['name'],
                        'arguments': json.dumps(message['message']['arguments'], indent=2),
                    }
                    next_message['content'] = ""
                else:
                    next_message['content'] = message['message']
            elif role == "function":
                next_message['content'] = json.dumps(message['message'])
                next_message['name'] = message['message_metadata']['name']
            else:
                next_message['content'] = message['message']
            chat_messages.append(next_message)
        return chat_messages

    def message_content_from_dict(self, message):
        """
        Extract the content from a message dict.

        :param message: Message
        :type message: dict
        :returns: Content
        :rtype: str
        """
        content = message['content']
        if message['message_type'] == 'function_call':
            content = json.dumps(message['function_call'])
        return content

    def _extract_message_content(self, message):
        """
        Extract the content from an LLM message.

        :param message: Message
        :type message: dict
        :returns: Content
        :rtype: str
        """
        if isinstance(message, BaseMessage):
            message_dict = _convert_message_to_dict(message)
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

    def gen_title_thread(self, conversation):
        """
        Generate the title for a conversation in a separate thread.

        :param conversation: Conversation
        :type conversation: Conversation
        :returns: Title
        :rtype: str
        """
        self.log.info(f"Generating title for conversation {conversation.id}")
        # NOTE: This might need to be smarter in the future, but for now
        # it should be reasonable to assume that the second record is the
        # first user message we need for generating the title.
        success, messages, user_message = self.message.get_messages(conversation.id, limit=2)
        if success:
            user_content = messages[1]['message'][:constants.TITLE_GENERATION_MAX_CHARACTERS]
            new_messages = [
                self.message.build_message('system', constants.DEFAULT_TITLE_GENERATION_SYSTEM_PROMPT),
                self.message.build_message('user', "%s: %s" % (constants.DEFAULT_TITLE_GENERATION_USER_PROMPT, user_content)),
            ]
            new_messages = self.transform_messages_to_chat_messages(new_messages)
            new_messages = self.provider.prepare_messages_for_llm_chat(new_messages)
            llm = ChatLiteLLM(model_name=constants.API_BACKEND_DEFAULT_MODEL, temperature=0)
            try:
                result = llm(new_messages)
                title = self._extract_message_content(result)['message']
                title = title.replace("\n", ", ").strip().strip('\'"')
                self.log.info(f"Title generated for conversation {conversation.id}: {title}")
                success, conversation, user_message = self.conversation.edit_conversation_title(conversation.id, title)
                if success:
                    self.log.debug(f"Title saved for conversation {conversation.id}")
                    self.conversation_title = conversation.title
                    return
            except ValueError as e:
                return False, new_messages, e
        self.log.info(f"Failed to generate title for conversation: {str(user_message)}")

    def gen_title(self, conversation):
        """
        Generate the title for a conversation.

        :param conversation: Conversation
        :type conversation: Conversation
        """
        thread = threading.Thread(target=self.gen_title_thread, args=(conversation,))
        thread.start()

    def get_system_message(self, system_message='default'):
        """
        Get the system message.

        :param system_message: System message alias
        :type system_message: str
        :returns: System message
        :rtype: str
        """
        aliases = self.get_system_message_aliases()
        if system_message in aliases:
            system_message = aliases[system_message]
        return system_message

    def set_system_message(self, system_message='default'):
        """
        Set the system message.

        :param system_message: System message or alias
        :type system_message: str
        """
        self.system_message = self.get_system_message(system_message)
        self.system_message_alias = system_message if system_message in self.get_system_message_aliases() else None
        message = f"System message set to: {self.system_message}"
        self.log.info(message)
        return True, system_message, message

    def set_max_submission_tokens(self, max_submission_tokens=None, force=False):
        """
        Set the max submission tokens.

        :param max_submission_tokens: Max submission tokens
        :type max_submission_tokens: int
        :param force: Force setting max submission tokens
        :type force: bool
        """
        chat = self.provider.get_capability('chat')
        if chat or force:
            self.max_submission_tokens = max_submission_tokens or self.provider.max_submission_tokens()
            return True, self.max_submission_tokens, f"Max submission tokens set to {self.max_submission_tokens}"
        return False, None, "Setting max submission tokens not supported for this provider"

    def get_runtime_config(self):
        """
        Get the runtime configuration.

        :returns: Runtime configuration
        :rtype: str
        """
        output = """
* Max submission tokens: %s
* System message: %s
""" % (self.max_submission_tokens, self.system_message)
        return output

    def get_current_llm_config(self):
        """
        Get current LLM, provider and model name.

        :returns: LLM object, provider, model name
        :rtype: tuple
        """
        llm = self.override_llm or self.llm
        provider = self.override_provider or self.provider
        model_name = getattr(llm, provider.model_property_name)
        return llm, provider, model_name

    def get_system_message_aliases(self):
        """
        Get system message aliases from config.

        :returns: Dict of message aliases
        :rtype: dict
        """
        aliases = self.config.get('model.system_message')
        aliases['default'] = constants.SYSTEM_MESSAGE_DEFAULT
        return aliases

    def build_chat_message(self, role, content, message_type='content', message_metadata=''):
        """Build a chat message dict.

        :param role: Message role
        :type role: str
        :param content: Message content
        :type content: str
        :param message_type: Message type, defaults to 'content'
        :type message_type: str, optional
        :param message_metadata: Message metadata, defaults to ''
        :type message_metadata: str, optional
        :returns: Message object
        :rtype: dict
        """
        message = None
        if message_type == 'function_call':
            if role == 'assistant':
                message = {
                    "content": "",
                    "function_call": json.loads(content, strict=False),
                }
        elif message_type == 'function_response':
            if role == 'function':
                metadata = json.loads(message_metadata, strict=False)
                message = {
                    "content": content,
                    "name": metadata['name'],
                }
        if not message:
            message = {
                "content": content,
            }
        message['role'] = role
        message['message_type'] = message_type
        message['message_metadata'] = message_metadata
        return message


    def retrieve_old_messages(self, conversation_id=None, target_id=None):
        """
        Retrieve old messages for a conversation.

        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :param target_id: Target message id, defaults to None
        :type target_id: int, optional
        :returns: List of messages
        :rtype: list
        """
        old_messages = []
        if conversation_id:
            success, old_messages, message = self.message.get_messages(conversation_id, target_id=target_id)
            if not success:
                raise Exception(message)
            old_messages = self.add_message_functions_to_cache(old_messages)
        return old_messages

    def prepare_prompt_conversation_messages(self, prompt, conversation_id=None, system_message=None):
        """
        Prepare prompt conversation messages.

        :param prompt: Message to send to the LLM
        :type prompt: str
        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :param system_message: System message, defaults to None
        :type system_message: str, optional
        :returns: List of messages
        :rtype: list
        """
        new_messages = []
        old_messages = self.retrieve_old_messages(conversation_id)
        if len(old_messages) == 0:
            system_message = system_message or self.system_message
            new_messages.append(self.message.build_message('system', system_message))
        new_messages.append(self.message.build_message('user', prompt))
        return old_messages, new_messages

    def create_new_conversation_if_needed(self, conversation_id=None, title=None):
        """
        Create new conversation if it doesn't exist.

        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :param title: Conversation title, defaults to None
        :type title: str, optional
        :returns: Conversation object
        :rtype: Conversation
        """
        conversation_id = conversation_id or self.conversation_id
        if conversation_id:
            success, conversation, message = self.conversation.get_conversation(conversation_id)
            if not success:
                raise Exception(message)
        else:
            success, conversation, message = self.conversation.add_conversation(self.current_user.id, title=title)
            if not success:
                raise Exception(message)
        self.conversation_id = conversation.id
        self.conversation_title = conversation.title
        return conversation

    def add_new_messages_to_conversation(self, conversation_id, new_messages, title=None):
        """Add new messages to a conversation.

        :param conversation_id: Conversation id
        :type conversation_id: int
        :param new_messages: New messages
        :type new_messages: list
        :param title: Conversation title, defaults to None
        :type title: str, optional
        :returns: Conversation, last message
        :rtype: tuple
        """
        conversation = self.create_new_conversation_if_needed(conversation_id, title)
        _llm, provider, model_name = self.get_current_llm_config()
        preset = self.active_preset_name or ''
        last_message = None
        for m in new_messages:
            success, last_message, user_message = self.message.add_message(conversation.id, m['role'], m['message'], m['message_type'], m['message_metadata'], provider.name, model_name, preset)
            if not success:
                raise Exception(user_message)
        tokens = self.get_conversation_token_count()
        self.set_conversation_tokens(tokens)
        return conversation, last_message

    def add_message(self, role, message, message_type, metadata, conversation_id=None):
        """
        Add a new message to a conversation.

        :param role: Message role
        :type role: str
        :param message: Message content
        :type message: str
        :param message_type: Message type
        :type message_type: str
        :param metadata: Message metadata
        :type metadata: dict
        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :returns: Added message
        :rtype: Message
        """
        conversation_id = conversation_id or self.conversation_id
        _llm, provider, model_name = self.get_current_llm_config()
        preset = self.active_preset_name or ''
        success, message, user_message = self.message.add_message(conversation_id, role, message, message_type, metadata, provider.name, model_name, preset)
        if not success:
            raise Exception(user_message)
        return message

    def _build_chat_request(self, messages):
        """
        Build chat request for LLM.

        :param messages: Messages
        :type messages: list
        :returns: LLM, prepared messages
        :rtype: tuple
        """
        customizations = {}
        provider = self.override_provider or self.provider
        llm = self.override_llm
        if not llm:
            customizations = self.expand_functions(customizations)
            llm = self.make_llm(customizations)
            self.llm = llm
        # TODO: More elegant way to do this, probably on provider.
        model_configuration = {k: str(v) for k, v in dict(llm).items()}
        self.log.debug(f"LLM request with message count: {len(messages)}, model configuration: {json.dumps(model_configuration)}")
        messages = self.transform_messages_to_chat_messages(messages)
        messages = provider.prepare_messages_for_llm(messages)
        return llm, messages

    def _execute_llm_streaming(self, llm, messages, request_overrides):
        self.log.debug(f"Started streaming request at {util.current_datetime().isoformat()}")
        response = ""
        print_stream = request_overrides.get('print_stream', False)
        stream_callback = request_overrides.get('stream_callback', None)
        # Start streaming loop.
        self.streaming = True
        try:
            for chunk in llm.stream(messages):
                content = chunk.content
                response += content
                if print_stream:
                    print(content, end="", flush=True)
                if stream_callback:
                    stream_callback(content)
                if not self.streaming:
                    util.print_status_message(False, "Generation stopped")
                    break
        except ValueError as e:
            return False, messages, e
        finally:
            # End streaming loop.
            self.streaming = False
        self.log.debug(f"Stopped streaming response at {util.current_datetime().isoformat()}")
        return True, response, "Response received"

    def _execute_llm_non_streaming(self, llm, messages):
        self.log.info("Starting non-streaming request")
        try:
            response = llm(messages)
        except ValueError as e:
            return False, messages, e
        return True, response, "Response received"

    def _call_llm(self, messages, request_overrides=None):
        """
        Call the LLM.

        :param messages: Messages
        :type messages: list
        :param request_overrides: Request overrides, defaults to None
        :type request_overrides: dict, optional
        :returns: success, response, message
        :rtype: tuple
        """
        request_overrides = request_overrides or {}
        stream = request_overrides.get('stream', False)
        if not self.override_llm:
            success, response, user_message = self.extract_preset_configuration_from_overrides({'request_overrides': request_overrides})
            if not success:
                return success, None, user_message
            preset_name, preset_overrides, _overrides = response
            if preset_overrides:
                self.log.info(f"Preset overrides provided in request, overriding LLM: {preset_overrides}")
                success, _llm, user_message = self.set_override_llm(preset_name, preset_overrides)
                if not success:
                    return success, None, user_message
        self.log.debug(f"Calling LLM with message count: {len(messages)}")
        llm, messages = self._build_chat_request(messages)
        if stream:
            return self._execute_llm_streaming(llm, messages, request_overrides)
        else:
            return self._execute_llm_non_streaming(llm, messages)

    def set_current_user(self, user=None):
        """
        Set the current user.

        :param user: User object, defaults to None
        :type user: User, optional
        :returns: success, preset, message on preset activation, otherwise init the provider
        :rtype: tuple
        """
        self.log.debug(f"Setting current user to {user.username if user else None}")
        self.current_user = user
        if self.current_user:
            if self.current_user.default_preset:
                self.log.debug(f"Activating user default preset: {self.current_user.default_preset}")
                return self.activate_preset(self.current_user.default_preset)
        return self.init_provider()

    def conversation_data_to_messages(self, conversation_data):
        """
        Convert conversation data to list of messages.

        :param conversation_data: Conversation data dict
        :type conversation_data: dict
        :returns: List of messages
        :rtype: list
        """
        return conversation_data['messages']

    def delete_conversation(self, conversation_id=None):
        """Delete a conversation.

        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :returns: success, conversation, message
        :rtype: tuple
        """
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, message = self.conversation.delete_conversation(conversation_id)
        return self._handle_response(success, conversation, message)

    def set_title(self, title, conversation_id=None):
        """
        Set conversation title.

        :param title: New title
        :type title: str
        :param conversation_id: Conversation id, defaults to current
        :type conversation_id: int, optional
        :returns: success, conversation, message
        :rtype: tuple
        """
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, user_message = self.conversation.edit_conversation_title(conversation_id, title)
        if success:
            self.conversation_title = conversation.title
        return self._handle_response(success, conversation, user_message)

    def get_history(self, limit=20, offset=0, user_id=None):
        """
        Get conversation history.

        :param limit: Number of results, defaults to 20
        :type limit: int, optional
        :param offset: Result offset, defaults to 0
        :type offset: int, optional
        :param user_id: User id, defaults to current
        :type user_id: int, optional
        :returns: success, history dict, message
        :rtype: tuple
        """
        user_id = user_id if user_id else self.current_user.id
        success, conversations, message = self.conversation.get_conversations(user_id, limit=limit, offset=offset)
        if success:
            history = {m.id: self.conversation.orm.object_as_dict(m) for m in conversations}
            return success, history, message
        return self._handle_response(success, conversations, message)

    def get_conversation(self, id=None):
        """
        Get a conversation.

        :param id: Conversation id, defaults to current
        :type id: int, optional
        :returns: success, conversation dict, message
        :rtype: tuple
        """
        id = id if id else self.conversation_id
        if not id:
            return False, None, "No current conversation"
        success, conversation, message = self.conversation.get_conversation(id)
        if success:
            success, messages, message = self.message.get_messages(id)
            if success:
                conversation_data = {
                    "conversation": self.conversation.orm.object_as_dict(conversation),
                    "messages": messages,
                }
                return success, conversation_data, message
        return self._handle_response(success, conversation, message)

    def new_conversation(self):
        """Start a new conversation."""
        super().new_conversation()
        self.set_conversation_tokens(0)

    def _strip_out_messages_over_max_tokens(self, messages, token_count, max_tokens):
        """
        Recursively strip out messages over max tokens.

        :param messages: Messages
        :type messages: list
        :param token_count: Token count
        :type token_count: int
        :param max_tokens: Max tokens
        :type max_tokens: int
        :returns: Messages
        :rtype: list
        """
        if token_count is not None:
            self.log.debug(f"Stripping messages over max tokens: {max_tokens}")
            stripped_messages_count = 0
            while token_count > max_tokens and len(messages) > 1:
                message = messages.pop(0)
                token_count = self.get_num_tokens_from_messages(messages)
                self.log.debug(f"Stripping message: {message['role']}, {message['message']} -- new token count: {token_count}")
                stripped_messages_count += 1
            token_count = self.get_num_tokens_from_messages(messages)
            if token_count > max_tokens:
                raise Exception(f"No messages to send, all messages have been stripped, still over max submission tokens: {max_tokens}")
            if stripped_messages_count > 0:
                max_tokens_exceeded_warning = f"Conversation exceeded max submission tokens ({max_tokens}), stripped out {stripped_messages_count} oldest messages before sending, sent {token_count} tokens instead"
                self.log.warning(max_tokens_exceeded_warning)
                util.print_status_message(False, max_tokens_exceeded_warning)
        return messages

    def _prepare_ask_request(self, prompt, system_message=None):
        """
        Prepare the request for the LLM.

        :param prompt: Message to send to the LLM
        :type prompt: str
        :param system_message: System message
        :type system_message: str
        :returns: New messages, messages
        :rtype: tuple
        """
        old_messages, new_messages = self.prepare_prompt_conversation_messages(prompt, self.conversation_id, system_message=system_message)
        messages = old_messages + new_messages
        messages = self._strip_out_messages_over_max_tokens(messages, self.conversation_tokens, self.max_submission_tokens)
        return new_messages, messages

    def _store_conversation_messages(self, conversation_id, new_messages, response_content, title=None):
        """
        Store conversation messages.

        :param conversation_id: Conversation id
        :type conversation_id: int
        :param new_messages: New messages
        :type new_messages: list
        :param response_content: Response content
        :type response_content: str
        :param title: Title
        :type title: str, optional
        :returns: success, conversation, message
        :rtype: tuple
        """
        conversation_id = conversation_id or self.conversation_id
        self.log.debug(f"Storing conversation messages for conversation {conversation_id}")
        if self.current_user:
            conversation, last_message = self.add_new_messages_to_conversation(conversation_id, new_messages, title)
            if conversation.title:
                self.log.debug(f"Conversation {conversation.id} already has title: {conversation.title}")
            else:
                self.gen_title(conversation)
            return True, conversation, "Conversation updated with new messages"
        else:
            return True, response_content, "No current user, conversation not saved"

    def _ask(self, input, request_overrides: dict = None):
        """
        Ask the LLM a question, return and optionally stream a response.

        :param input: The input to be sent to the LLM.
        :type input: str
        :request_overrides: Overrides for this specific request.
        :type request_overrides: dict, optional
        :returns: success, LLM response, message
        :rtype: tuple
        """
        self.log.info("Starting 'ask' request")
        request_overrides = request_overrides or {}
        system_message = request_overrides.get('system_message')
        new_messages, messages = self._prepare_ask_request(input, system_message=system_message)
        success, response_obj, user_message = self._call_llm(messages, request_overrides)
        if success:
            response_content, new_messages = self.post_response(response_obj, new_messages, request_overrides)
            self.message_clipboard = response_content
            title = request_overrides.get('title')
            success, response_obj, user_message = self._store_conversation_messages(self.conversation_id, new_messages, response_content, title)
            if success:
                response_obj = response_content
        self.set_override_llm()
        return self._handle_response(success, response_obj, user_message)

    def ask_stream(self, input: str, request_overrides: dict = None):
        """
        Ask the LLM a question and stream a response.

        :param input: The input to be sent to the LLM.
        :type input: str
        :request_overrides: Overrides for this specific request.
        :type request_overrides: dict, optional
        :returns: success, LLM response, message
        :rtype: tuple
        """
        request_overrides = request_overrides or {}
        request_overrides['stream'] = True
        return self._ask(input, request_overrides)

    def ask(self, input: str, request_overrides: dict = None):
        """
        Ask the LLM a question and return response.

        :param input: The input to be sent to the LLM.
        :type input: str
        :request_overrides: Overrides for this specific request.
        :type request_overrides: dict, optional
        :returns: success, LLM response, message
        :rtype: tuple
        """
        return self._ask(input, request_overrides)
