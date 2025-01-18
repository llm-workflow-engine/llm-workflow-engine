import copy
import os

from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.backends.api.database import Database
from lwe.backends.api.orm import Orm, User
from lwe.core.cache_manager import CacheManager
from lwe.core.template_manager import TemplateManager
from lwe.core.preset_manager import PresetManager
from lwe.core.provider_manager import ProviderManager
from lwe.core.workflow_manager import WorkflowManager
from lwe.core.tool_manager import ToolManager
from lwe.core.plugin_manager import PluginManager
import lwe.core.constants as constants
import lwe.core.util as util
from lwe.backends.api.request import ApiRequest
from lwe.backends.api.conversation_storage_manager import ConversationStorageManager
from lwe.backends.api.user import UserManager
from lwe.backends.api.conversation import ConversationManager
from lwe.backends.api.message import MessageManager
from lwe.backends.api.orm import Conversation
from lwe.core.preset_manager import parse_llm_dict

ADDITIONAL_PLUGINS = [
    "provider_chat_openai",
]


class ApiBackend:
    """Backend implementation using direct API access."""

    name = "api"

    def __init__(self, config=None, orm=None):
        """
        Initializes the Backend instance.

        This method sets up attributes that should only be initialized once.

        :param config: Optional configuration for the backend. If not provided, it uses a default configuration.
        """
        self.config = config or Config()
        self.conversation_id = None
        self.conversation_title = None
        self.current_user = None
        self.request = None
        self.logfile = None
        self.orm = orm or Orm(config)
        self.user_manager = UserManager(config, self.orm)
        self.conversation = ConversationManager(config, self.orm)
        self.message = MessageManager(config, self.orm)
        self.initialize_database()
        self.initialize_backend(self.config)
        self.initialize_file_logging()

    def set_available_models(self):
        """
        Sets the available models for the provider.
        """
        self.available_models = self.provider.available_models

    def make_llm(self, customizations=None):
        """
        Creates a Language Model (llm) using the provider.

        :param customizations: Optional dictionary for customizations.
        :return: Language Model (llm) object.
        """
        customizations = customizations or {}
        llm = self.provider.make_llm(customizations)
        return llm

    def terminate_stream(self, _signal, _frame):
        """
        Handles termination signal, passing it to the request if present.

        :param _signal: The signal that triggered the termination.
        :param _frame: Current stack frame.
        """
        self.log.info("Received signal to terminate stream")
        self.request and self.request.terminate_stream(_signal, _frame)

    def run_template_setup(self, template_name, substitutions=None):
        """
        Sets up the run of a template.

        :param template_name: Name of the template to run.
        :param substitutions: Optional dictionary of substitutions.
        :return: A tuple containing a success indicator, tuple of template setup data, and a user message.
        """
        self.log.info(f"Setting up run of template: {template_name}")
        substitutions = substitutions or {}
        message, overrides = self.template_manager.build_message_from_template(
            template_name, substitutions
        )
        return True, (message, overrides), f"Set up of template run complete: {template_name}"

    def run_template_compiled(self, message, overrides=None):
        """
        Runs the compiled template.

        :param message: The message to be sent.
        :param overrides: Optional dictionary of overrides.
        :return: The response tuple from LLM request.
        """
        overrides = overrides or {}
        self.log.info("Running template")
        response = self.make_request(message, **overrides)
        return response

    def build_message_from_template(self, template_name, template_vars=None, overrides=None):
        """
        Builds the message from the template.

        :param template_name: Name of the template to run.
        :param template_vars: Optional dictionary of template variables.
        :param overrides: Optional dictionary of overrides.
        :return: A tuple containing a success indicator, tuple of built message and overrides, and a user message.
        """
        template_vars = template_vars or {}
        overrides = overrides or {}
        (
            success,
            response,
            user_message,
        ) = self.template_manager.get_template_variables_substitutions(template_name)
        if not success:
            return success, response, user_message
        _template, _variables, substitutions = response
        util.merge_dicts(substitutions, template_vars)
        success, response, user_message = self.run_template_setup(template_name, substitutions)
        if not success:
            return success, response, user_message
        message, template_overrides = response
        util.merge_dicts(template_overrides, overrides)
        return True, (message, template_overrides), f"Built message from template: {template_name}"

    def run_template(self, template_name, template_vars=None, overrides=None):
        """
        Runs the given template with the provided variables and overrides.

        :param template_name: Name of the template to run.
        :param template_vars: Optional dictionary of template variables, will merged with any set in the template.
        :param overrides: Optional dictionary of overrides, will be merged with any set in the template.
        :return: The response tuple from the template run.
        """
        success, response, user_message = self.build_message_from_template(
            template_name, template_vars=template_vars, overrides=overrides
        )
        if not success:
            return success, response, user_message
        message, overrides = response
        response = self.run_template_compiled(message, overrides)
        return response

    def initialize_backend(self, config=None):
        """
        Initializes the backend with provided or default configuration,
        and sets up necessary attributes.

        This method is safe to call for dynamically reloading backends.

        :param config: Backend configuration options
        :type config: dict, optional
        """
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.provider_name = None
        self.provider = None
        self.message_clipboard = None
        self.return_only = False
        self.cache_manager = CacheManager(self.config)
        self.template_manager = TemplateManager(self.config)
        self.preset_manager = PresetManager(self.config)
        self.plugin_manager = PluginManager(
            self.config, self, self.cache_manager, additional_plugins=ADDITIONAL_PLUGINS
        )
        self.provider_manager = ProviderManager(self.config, self.plugin_manager)
        self.workflow_manager = WorkflowManager(self.config)
        self.tool_manager = ToolManager(self.config)
        self.workflow_manager.load_workflows()
        self.init_provider()
        self.set_available_models()
        self.set_conversation_tokens(0)
        self.auto_create_first_user()
        self.load_default_user()
        self.load_default_conversation()

    def initialize_database(self):
        database = Database(self.config, orm=self.orm)
        database.create_schema()

    def auto_create_first_user(self):
        username = self.config.get("backend_options.auto_create_first_user")
        if isinstance(username, str):
            query = self.user_manager.session.query(User).order_by(User.id).limit(1)
            first_user = query.first()
            if not first_user:
                first_user = self.user_manager.orm_add_user(username, None, None)
            return first_user

    def load_default_user(self):
        default_user = self.config.get("backend_options.default_user")
        if default_user is not None:
            self.load_user(default_user)

    def load_default_conversation(self):
        default_conversation_id = self.config.get("backend_options.default_conversation_id")
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
        success, _alias, user_message = self.set_system_message(
            self.config.get("model.default_system_message")
        )
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
        default_preset = self.config.get("model.default_preset")
        if default_preset:
            success, preset, user_message = self.activate_preset(default_preset)
            if success:
                return
            util.print_status_message(
                False, f"Failed to load default preset {default_preset}: {user_message}"
            )
        self.set_provider("provider_chat_openai")

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
        self.log.debug(
            f"Setting provider to: {provider_name}, with customizations: {customizations}, reset: {reset}"
        )
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
                    (
                        success,
                        customizations,
                        customization_message,
                    ) = self.provider.set_customization_value(key, value)
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
        success, customizations, user_message = self.provider.set_model(model_name)
        if success:
            self.model = model_name
            self.set_max_submission_tokens()
        return success, customizations, user_message

    def make_preset(self):
        """Make preset from current provider customizations."""
        metadata, customizations = parse_llm_dict(self.provider.customizations)
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
        customizations = copy.deepcopy(customizations)
        success, provider, user_message = self.set_provider(
            metadata["provider"], customizations, reset=True
        )
        if success:
            self.active_preset = preset
            self.active_preset_name = preset_name
            if "system_message" in metadata:
                self.set_system_message(metadata["system_message"])
            if "max_submission_tokens" in metadata:
                self.set_max_submission_tokens(metadata["max_submission_tokens"])
        return success, preset, user_message

    def reload_plugin(self, plugin_name):
        """
        Reload a plugin.

        :param plugin_name: Name of plugin
        :type plugin_name: str
        :returns: success, plugin_instance, message
        :rtype: tuple
        """
        return self.plugin_manager.reload_plugin(plugin_name)

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

    def set_conversation_tokens(self, tokens):
        """
        Set current conversation token count.

        :param tokens: Number of conversation tokens
        :type tokens: int
        """
        if self.conversation_id is None:
            provider = self.provider
        else:
            success, last_message, user_message = self.message.get_last_message(
                self.conversation_id
            )
            if not success:
                raise ValueError(user_message)
            provider = self.provider_manager.get_provider_from_name(last_message["provider"])
        if provider is not None and provider.get_capability("chat"):
            self.conversation_tokens = tokens
        else:
            self.conversation_tokens = None

    def switch_to_conversation(self, conversation_id):
        """
        Switch to a conversation.

        :param conversation_id: Conversation id
        :type conversation_id: int
        """
        self.log.debug(f"Switching to conversation {conversation_id}")
        success, conversation, user_message = self.get_conversation(conversation_id)
        if success:
            self.conversation_id = conversation_id
            self.conversation_title = conversation["conversation"]["title"]
        else:
            raise ValueError(user_message)
        success, last_message, user_message = self.message.get_last_message(self.conversation_id)
        if not success:
            raise ValueError(user_message)
        model_configured = False
        self.log.debug(f"Retrieved last message {last_message}")
        if last_message["preset"]:
            self.log.debug(f"Last message has preset: {last_message['preset']}")
            success, _preset, user_message = self.activate_preset(last_message["preset"])
            if success:
                model_configured = True
            else:
                util.print_status_message(
                    False,
                    f"Unable to switch conversation to previous preset {last_message['preset']!r} -- ERROR: {user_message}, falling back to provider: {last_message['provider']}, model: {last_message['model']}",
                )
        if not model_configured:
            if last_message["provider"] and last_message["model"]:
                self.log.debug(
                    f"Last message has provider: {last_message['provider']}, model: {last_message['model']}"
                )
                success, _provider, _user_message = self.set_provider(
                    last_message["provider"], reset=True
                )
                if success:
                    success, _customizations, _user_message = self.set_model(last_message["model"])
                    if success:
                        self.init_system_message()
                        model_configured = True
        if not model_configured:
            message = "Invalid conversation provider/model, falling back to default provider/model"
            self.log.warning(message)
            util.print_status_message(False, message)
            self.init_provider()
        conversation_storage_manager = ConversationStorageManager(
            self.config,
            self.tool_manager,
            self.current_user,
            self.conversation_id,
            self.provider,
            self.model,
            self.active_preset_name or "",
            provider_manager=self.provider_manager,
            orm=self.orm,
        )
        tokens = conversation_storage_manager.get_conversation_token_count()
        self.set_conversation_tokens(tokens)
        self.write_log_context()

    def get_system_message(self, system_message="default"):
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

    def set_system_message(self, system_message="default"):
        """
        Set the system message.

        :param system_message: System message or alias
        :type system_message: str
        """
        self.system_message = self.get_system_message(system_message)
        self.system_message_alias = (
            system_message if system_message in self.get_system_message_aliases() else None
        )
        message = f"System message set to: {self.system_message}"
        self.log.info(message)
        return True, system_message, message

    def set_max_submission_tokens(self, max_submission_tokens=None):
        """
        Set the max submission tokens.

        :param max_submission_tokens: Max submission tokens
        :type max_submission_tokens: int
        :param force: Force setting max submission tokens
        :type force: bool
        """
        self.max_submission_tokens = max_submission_tokens or self.provider.max_submission_tokens()
        return (
            True,
            self.max_submission_tokens,
            f"Max submission tokens set to {self.max_submission_tokens}",
        )

    def get_runtime_config(self):
        """
        Get the runtime configuration.

        :returns: Runtime configuration
        :rtype: str
        """
        output = """
* Max submission tokens: %s
* System message: %s
""" % (
            self.max_submission_tokens,
            self.system_message,
        )
        return output

    def get_system_message_aliases(self):
        """
        Get system message aliases from config.

        :returns: Dict of message aliases
        :rtype: dict
        """
        aliases = self.config.get("model.system_message")
        aliases["default"] = constants.SYSTEM_MESSAGE_DEFAULT
        return aliases

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
            success, old_messages, message = self.message.get_messages(
                conversation_id, target_id=target_id
            )
            if not success:
                raise Exception(message)
        return old_messages

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
                self.log.debug(
                    f"Activating user default preset: {self.current_user.default_preset}"
                )
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
        return conversation_data["messages"]

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
        success, conversation, user_message = self.conversation.edit_conversation_title(
            conversation_id, title
        )
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
        success, conversations, message = self.conversation.get_conversations(
            user_id, limit=limit, offset=offset
        )
        if success:
            history = {m.id: self.orm.object_as_dict(m) for m in conversations}
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
                    "conversation": self.orm.object_as_dict(conversation),
                    "messages": messages,
                }
                return success, conversation_data, message
        return self._handle_response(success, conversation, message)

    def get_current_conversation_title(self):
        if not self.conversation_id:
            return None
        if self.conversation_title:
            return self.conversation_title
        success, conversation, message = self.conversation.get_conversation(self.conversation_id)
        return success and conversation.title or None

    def new_conversation(self):
        """Start a new conversation."""
        self.conversation_id = None
        self.conversation_title = None
        self.message_clipboard = None
        self.set_conversation_tokens(0)
        self.write_log_context()

    def write_log(self, prompt, response):
        """Write prompt and response to log file if logging is enabled."""
        if self.logfile is not None:
            contents = f"""
USER:

{prompt}

ASSISTANT:

{response}

"""
            try:
                self.logfile.write(contents)
            except OSError as e:
                message = f"Failed to write content to log file '{self.logfile.name}': {e}"
                self.log.error(message)
            self.write_log_context()

    def write_log_context(self):
        """Write current conversation context to log file if logging is enabled."""
        if self.logfile is not None:
            try:
                self.logfile.write(f"## context {self.conversation_id}\n")
                self.logfile.flush()
            except OSError as e:
                message = f"Failed to write log context to log file '{self.logfile.name}': {e}"
                self.log.error(message)

    def initialize_file_logging(self):
        """Initialize file logging based on configuration."""
        if self.config.get("chat.log.enabled"):
            log_file = self.config.get("chat.log.filepath")
            if log_file:
                self.open_log(log_file)

    def open_log(self, filename):
        """Open a log file for writing."""
        self.close_log()
        self.log.debug(f"Opening log file '{filename}'")
        try:
            if not os.path.isabs(filename):
                filename = os.path.join(os.getcwd(), filename)
            self.logfile = open(filename, "a", encoding="utf-8")
            self.log.debug(f"Opened log file '{self.logfile.name}'")
            return True
        except OSError as e:
            message = f"Failed to open log file '{filename}': {e}"
            self.log.error(message)
            return False

    def close_log(self):
        """Close the current log file if one is open."""
        if self.logfile is not None:
            self.log.debug("Closing log file")
            self.logfile.close()
            self.logfile = None

    def make_request(self, input, request_overrides: dict = None):
        """
        Ask the LLM a question, return and optionally stream a response.

        :param input: The input to be sent to the LLM, can be a string for a single user message, or a list of message dicts with 'role' and 'content' keys.
        :type input: str | list
        :request_overrides: Overrides for this specific request.
        :type request_overrides: dict, optional
        :returns: success, LLM response, message
        :rtype: tuple
        """
        self.log.info("Starting 'ask' request")
        request_overrides = request_overrides or {}
        old_messages = self.retrieve_old_messages(self.conversation_id)
        self.log.debug(
            f"Extracting activate preset configuration from request_overrides: {request_overrides}"
        )
        success, response, user_message = util.extract_preset_configuration_from_request_overrides(
            request_overrides, self.active_preset_name
        )
        if not success:
            return success, response, user_message
        preset_name, _preset_overrides, activate_preset = response
        request = ApiRequest(
            self.config,
            self.provider,
            self.provider_manager,
            self.tool_manager,
            input,
            self.active_preset,
            self.preset_manager,
            self.system_message,
            old_messages,
            self.max_submission_tokens,
            request_overrides,
            orm=self.orm,
        )
        self.request = request
        request.set_request_llm()
        new_messages, messages = request.prepare_ask_request()
        success, response_obj, user_message = request.call_llm(messages)
        files = request_overrides.get("files", [])
        if files:
            self.log.debug("Files attached, returning directly")
            self.request = None
            response_content = response_obj and response_obj.content or response_obj
            return self._handle_response(success, response_content, user_message)
        if success:
            response_data = (
                vars(response_obj) if hasattr(response_obj, "__dict__") else f"{response_obj}"
            )
            self.log.debug(f"LLM Response: {response_data}")
            response_content, new_messages = request.post_response(response_obj, new_messages)
            self.message_clipboard = response_content
            title = request_overrides.get("title")
            conversation_storage_manager = ConversationStorageManager(
                self.config,
                self.tool_manager,
                self.current_user,
                self.conversation_id,
                request.provider,
                request.model_name,
                request.preset_name,
                provider_manager=self.provider_manager,
                orm=self.orm,
            )
            (
                success,
                response_obj,
                user_message,
            ) = conversation_storage_manager.store_conversation_messages(
                new_messages, response_content, title
            )
            if success:
                if isinstance(response_obj, Conversation):
                    conversation = response_obj
                    self.conversation_id = conversation.id
                    self.conversation_title = conversation.title
                    tokens = conversation_storage_manager.get_conversation_token_count()
                    self.set_conversation_tokens(tokens)
                response_obj = response_content
                if activate_preset:
                    self.log.info(f"Activating preset from request override: {preset_name}")
                    self.activate_preset(preset_name)
                self.write_log(input, response_obj)
        self.request = None
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
        request_overrides["stream"] = True
        return self.make_request(input, request_overrides)

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
        return self.make_request(input, request_overrides)
