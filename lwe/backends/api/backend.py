import json
import threading
import tiktoken

from langchain.chat_models.openai import ChatOpenAI
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

    name = "api"

    def __init__(self, config=None):
        super().__init__(config)
        self.user_manager = UserManager(self.config)
        self.conversation = ConversationManager(self.config)
        self.message = MessageManager(self.config)
        self.current_user = None
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
        if isinstance(identifier, int):
            success, user, user_message = self.user_manager.get_by_user_id(identifier)
        else:
            success, user, user_message = self.user_manager.get_by_username_or_email(identifier)
        if not success or not user:
            raise Exception(user_message)
        self.set_current_user(user)

    def load_conversation(self, conversation_id):
        success, conversation_data, user_message = self.get_conversation(conversation_id)
        if success:
            if conversation_data:
                messages = self.conversation_data_to_messages(conversation_data)
                message = messages.pop()
                self.switch_to_conversation(conversation_id, message['id'])
                return
            else:
                user_message = "Missing conversation data"
        raise Exception(user_message)

    def init_system_message(self):
        success, _alias, user_message = self.set_system_message(self.config.get('model.default_system_message'))
        if not success:
            util.print_status_message(success, user_message)
            self.set_system_message()

    def get_providers(self):
        return self.provider_manager.get_provider_plugins()

    def init_provider(self):
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
            if not customizations or 'streaming' not in customizations:
                self.set_provider_streaming()
            self.llm = self.make_llm()
            self.set_model(getattr(self.llm, self.provider.model_property_name))
        return success, provider, user_message

    # TODO: This feels hacky, perhaps better to have a shell register itself
    # for output from the backend?
    def set_return_only(self, return_only=False):
        self.return_only = return_only

    def set_model(self, model_name):
        self.log.debug(f"Setting model to: {model_name}")
        success, customizations, user_message = super().set_model(model_name)
        self.set_max_submission_tokens(force=True)
        return success, customizations, user_message

    def set_override_llm(self, preset_name=None):
        if preset_name:
            self.log.info(f"Setting override LLM to preset: {preset_name}")
            success, preset, user_message = self.preset_manager.ensure_preset(preset_name)
            if success:
                metadata, customizations = preset
                customizations = self.expand_functions(customizations)
                success, provider, user_message = self.provider_manager.load_provider(metadata['provider'])
                if success:
                    if self.stream and self.should_stream() and not self.return_only:
                        self.log.debug("Adding streaming-specific customizations to LLM request")
                        customizations.update(self.streaming_args(interrupt_handler=True))
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
        if 'model_kwargs' in customizations and 'functions' in customizations['model_kwargs']:
            customizations['model_kwargs']['functions'] = [f['name'] for f in customizations['model_kwargs']['functions']]
        return customizations

    def make_preset(self):
        metadata, customizations = parse_llm_dict(self.provider.customizations)
        customizations = self.compact_functions(customizations)
        return metadata, customizations

    def activate_preset(self, preset_name):
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
        if not success:
            self.log.error(message)
        return success, obj, message

    def get_token_encoding(self, model="gpt-3.5-turbo"):
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
        if not encoding:
            encoding = self.get_token_encoding()
        """Returns the number of tokens used by a list of messages."""
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

    def switch_to_conversation(self, conversation_id, parent_message_id):
        super().switch_to_conversation(conversation_id, parent_message_id)
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
        conversation_id = conversation_id or self.conversation_id
        success, old_messages, user_message = self.message.get_messages(conversation_id)
        if not success:
            raise Exception(user_message)
        tokens = self.get_num_tokens_from_messages(old_messages)
        return tokens

    def extract_system_message_from_overrides(self, request_overrides):
        system_message = None
        if 'system_message' in request_overrides:
            system_message = request_overrides.pop('system_message')
            system_message = self.get_system_message(system_message)
        return system_message, request_overrides

    def should_return_on_function_call(self):
        preset = self.override_preset or self.active_preset
        if preset:
            metadata, _customizations = preset
            if 'return_on_function_call' in metadata and metadata['return_on_function_call']:
                return True
        return False

    def is_function_response_message(self, message):
        return message['message_type'] == 'function_response'

    def check_return_on_function_response(self, new_messages):
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
        preset = self.override_preset or self.active_preset
        if preset:
            _metadata, customizations = preset
            if 'model_kwargs' in customizations and 'function_call' in customizations['model_kwargs'] and isinstance(customizations['model_kwargs']['function_call'], dict):
                return True
        return False

    def run_function(self, function_name, data):
        success, response, user_message = self.function_manager.run_function(function_name, data)
        json_obj = response if success else {'error': user_message}
        if not self.return_only:
            util.print_markdown(f"### Function response:\n* Name: {function_name}\n* Success: {success}")
            util.print_markdown(json_obj)
        return success, json_obj, user_message

    def post_response(self, response_obj, new_messages, request_overrides):
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
            return function_response, new_messages
        return response_message['message'], new_messages

    def transform_messages_to_chat_messages(self, messages):
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
        content = message['content']
        if message['message_type'] == 'function_call':
            content = json.dumps(message['function_call'])
        return content

    def _extract_message_content(self, message):
        if isinstance(message, BaseMessage):
            message_dict = _convert_message_to_dict(message)
            content = message_dict['content']
            message_type = 'content'
            if 'function_call' in message_dict:
                message_type = 'function_call'
                message_dict['function_call']['arguments'] = json.loads(message_dict['function_call']['arguments'])
                content = message_dict['function_call']
            elif message_dict['role'] == 'function':
                message_type = 'function_response'
            return self.message.build_message(message_dict['role'], content, message_type)
        return self.message.build_message('assistant', message)

    def gen_title_thread(self, conversation):
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
            llm = ChatOpenAI(model_name=constants.API_BACKEND_DEFAULT_MODEL, temperature=0)
            try:
                result = llm(new_messages)
                title = self._extract_message_content(result)['message']
                title = title.replace("\n", ", ").strip()
                self.log.info(f"Title generated for conversation {conversation.id}: {title}")
                success, conversation, user_message = self.conversation.edit_conversation_title(conversation.id, title)
                if success:
                    self.log.debug(f"Title saved for conversation {conversation.id}")
                    return
            except ValueError as e:
                return False, new_messages, e
        self.log.info(f"Failed to generate title for conversation: {str(user_message)}")

    def gen_title(self, conversation):
        thread = threading.Thread(target=self.gen_title_thread, args=(conversation,))
        thread.start()

    def get_system_message(self, system_message='default'):
        aliases = self.get_system_message_aliases()
        if system_message in aliases:
            system_message = aliases[system_message]
        return system_message

    def set_system_message(self, system_message='default'):
        self.system_message = self.get_system_message(system_message)
        self.system_message_alias = system_message if system_message in self.get_system_message_aliases() else None
        message = f"System message set to: {self.system_message}"
        self.log.info(message)
        return True, system_message, message

    def set_max_submission_tokens(self, max_submission_tokens=None, force=False):
        chat = self.provider.get_capability('chat')
        if chat or force:
            self.max_submission_tokens = max_submission_tokens or self.provider.max_submission_tokens()
            return True, self.max_submission_tokens, f"Max submission tokens set to {self.max_submission_tokens}"
        return False, None, "Setting max submission tokens not supported for this provider"

    def get_runtime_config(self):
        output = """
* System message: %s
""" % (self.system_message)
        return output

    def get_current_llm_config(self):
        llm = self.override_llm or self.llm
        provider = self.override_provider or self.provider
        model_name = getattr(llm, provider.model_property_name)
        return llm, provider, model_name

    def get_system_message_aliases(self):
        aliases = self.config.get('model.system_message')
        aliases['default'] = constants.SYSTEM_MESSAGE_DEFAULT
        return aliases

    def build_chat_message(self, role, content, message_type='content', message_metadata=''):
        message = None
        if message_type == 'function_call':
            if role == 'assistant':
                message = {
                    "content": "",
                    "function_call": json.loads(content),
                }
        elif message_type == 'function_response':
            if role == 'function':
                metadata = json.loads(message_metadata)
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
        old_messages = []
        if conversation_id:
            success, old_messages, message = self.message.get_messages(conversation_id, target_id=target_id)
            if not success:
                raise Exception(message)
            old_messages = self.add_message_functions_to_cache(old_messages)
        return old_messages

    def prepare_prompt_conversation_messages(self, prompt, conversation_id=None, target_id=None, system_message=None):
        new_messages = []
        old_messages = self.retrieve_old_messages(conversation_id, target_id)
        if len(old_messages) == 0:
            system_message = system_message or self.system_message
            new_messages.append(self.message.build_message('system', system_message))
        new_messages.append(self.message.build_message('user', prompt))
        return old_messages, new_messages

    def create_new_conversation_if_needed(self, conversation_id=None, title=None):
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
        return conversation

    def add_new_messages_to_conversation(self, conversation_id, new_messages, title=None):
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
        conversation_id = conversation_id or self.conversation_id
        _llm, provider, model_name = self.get_current_llm_config()
        preset = self.active_preset_name or ''
        success, message, user_message = self.message.add_message(conversation_id, role, message, message_type, metadata, provider.name, model_name, preset)
        if not success:
            raise Exception(user_message)
        return message

    def _build_chat_request(self, messages, customizations=None):
        customizations = customizations or {}
        provider = self.override_provider or self.provider
        llm = self.override_llm
        if not llm:
            if self.stream and self.should_stream() and not self.return_only:
                self.log.debug("Adding streaming-specific customizations to LLM request")
                customizations.update(self.streaming_args(interrupt_handler=True))
            customizations = self.expand_functions(customizations)
            llm = self.make_llm(customizations)
            self.llm = llm
        # TODO: More elegant way to do this, probably on provider.
        model_configuration = {k: str(v) for k, v in dict(llm).items()}
        self.log.debug(f"LLM request with message count: {len(messages)}, model configuration: {json.dumps(model_configuration)}")
        messages = self.transform_messages_to_chat_messages(messages)
        messages = provider.prepare_messages_for_llm(messages)
        return llm, messages

    def _call_llm(self, messages, customizations=None):
        customizations = customizations or {}
        self.log.debug(f"Calling LLM with message count: {len(messages)}")
        llm, messages = self._build_chat_request(messages, customizations)
        try:
            response = llm(messages)
        except ValueError as e:
            return False, messages, e
        return True, response, "Response received"

    def set_current_user(self, user=None):
        self.log.debug(f"Setting current user to {user.username if user else None}")
        self.current_user = user
        if self.current_user:
            if self.current_user.default_preset:
                self.log.debug(f"Activating user default preset: {self.current_user.default_preset}")
                return self.activate_preset(self.current_user.default_preset)
        return self.init_provider()

    def conversation_data_to_messages(self, conversation_data):
        return conversation_data['messages']

    def delete_conversation(self, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, message = self.conversation.delete_conversation(conversation_id)
        return self._handle_response(success, conversation, message)

    def set_title(self, title, conversation_id=None):
        conversation_id = conversation_id if conversation_id else self.conversation_id
        success, conversation, user_message = self.conversation.edit_conversation_title(conversation_id, title)
        return self._handle_response(success, conversation, user_message)

    def get_history(self, limit=20, offset=0, user_id=None):
        user_id = user_id if user_id else self.current_user.id
        success, conversations, message = self.conversation.get_conversations(user_id, limit=limit, offset=offset)
        if success:
            history = {m.id: self.conversation.orm.object_as_dict(m) for m in conversations}
            return success, history, message
        return self._handle_response(success, conversations, message)

    def get_conversation(self, id=None):
        id = id if id else self.conversation_id
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
        super().new_conversation()
        self.set_conversation_tokens(0)

    def _strip_out_messages_over_max_tokens(self, messages, token_count, max_tokens):
        if token_count is not None:
            stripped_messages_count = 0
            while token_count > max_tokens and len(messages) > 1:
                message = messages.pop(0)
                token_count = self.get_num_tokens_from_messages(messages)
                self.log.debug(f"Stripping message: {message['role']}, {message['content']} -- new token count: {token_count}")
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
        old_messages, new_messages = self.prepare_prompt_conversation_messages(prompt, self.conversation_id, self.parent_message_id, system_message=system_message)
        messages = old_messages + new_messages
        messages = self._strip_out_messages_over_max_tokens(messages, self.conversation_tokens, self.max_submission_tokens)
        return new_messages, messages

    def _store_conversation_messages(self, conversation_id, new_messages, response_content, title=None):
        conversation_id = conversation_id or self.conversation_id
        self.log.debug(f"Storing conversation messages for conversation {conversation_id}")
        if self.current_user:
            conversation, last_message = self.add_new_messages_to_conversation(conversation_id, new_messages, title)
            self.parent_message_id = last_message.id
            if conversation.title:
                self.log.debug(f"Conversation {conversation.id} already has title: {conversation.title}")
            else:
                self.gen_title(conversation)
            return True, conversation, "Conversation updated with new messages"
        else:
            return True, response_content, "No current user, conversation not saved"

    def _ask(self, prompt, title=None, request_overrides=None):
        stream = self.stream and self.should_stream()
        self.log.info(f"Starting {stream and 'streaming' or 'non-streaming'} request")
        request_overrides = request_overrides or {}
        system_message, request_overrides = self.extract_system_message_from_overrides(request_overrides)
        new_messages, messages = self._prepare_ask_request(prompt, system_message=system_message)
        if stream:
            # Start streaming loop.
            self.streaming = True
            self.log.debug(f"Started streaming response at {util.current_datetime().isoformat()}")
        success, response_obj, user_message = self._call_llm(messages, request_overrides)
        if stream:
            self.log.debug(f"Stopped streaming response at {util.current_datetime().isoformat()}")
            if success and not self.streaming:
                util.print_status_message(False, "Generation stopped")
        if success:
            response_content, new_messages = self.post_response(response_obj, new_messages, request_overrides)
            self.message_clipboard = response_content
            success, response_obj, user_message = self._store_conversation_messages(self.conversation_id, new_messages, response_content, title)
            if success:
                response_obj = response_content
        if stream:
            # End streaming loop.
            self.streaming = False
        return self._handle_response(success, response_obj, user_message)

    def ask_stream(self, prompt, title=None, request_overrides=None):
        return self._ask(prompt, title, request_overrides)

    def ask(self, prompt, title=None, request_overrides=None):
        """
        Send a message to chatGPT and return the response.

        Args:
            message (str): The message to send.

        Returns:
            str: The response received from the model.
        """
        return self._ask(prompt, title, request_overrides)
