from abc import ABC, abstractmethod
from typing import Any

import lwe.core.monkey_patch

from langchain.callbacks.manager import CallbackManager, StreamInterruption
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from lwe.core.config import Config
from lwe.core.logger import Logger
from lwe.core.template import TemplateManager
from lwe.core.preset_manager import PresetManager
from lwe.core import util

class VerboseStreamingStdOutCallbackHandler(StreamingStdOutCallbackHandler):
    @property
    def always_verbose(self) -> bool:
        """Whether to call verbose callbacks even if verbose is False."""
        return True

def make_interrupt_streaming_callback_handler(backend):
    class InterruptStreamingCallbackHandler(VerboseStreamingStdOutCallbackHandler):
        def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
            if not backend.streaming:
                message = "Request to interrupt streaming"
                backend.log.info(message)
                raise StreamInterruption(message)
    return InterruptStreamingCallbackHandler()

class Backend(ABC):
    """
    Base class/interface for all backends.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.provider_name = None
        self.provider = None
        self.parent_message_id = None
        self.conversation_id = None
        self.conversation_title_set = None
        self.message_clipboard = None
        self.stream = False
        self.streaming = False
        self.interrupt_streaming_callback_handler = make_interrupt_streaming_callback_handler(self)
        self.template_manager = TemplateManager(self.config)
        self.preset_manager = PresetManager(self.config)

    def set_available_models(self):
        self.available_models = self.provider.available_models

    def set_provider_streaming(self, stream=None):
        self.log.debug("Setting provider streaming")
        if self.provider.can_stream():
            self.log.debug("Provider can stream")
            if stream is not None:
                self.stream = stream
            self.provider.set_customization_value('streaming', self.stream)
        else:
            self.log.debug("Provider cannot stream")
            if stream is not None:
                self.stream = stream
        self.log.info(f"Provider streaming is now: {self.stream}")

    def should_stream(self):
        # NOTE: No override_provider on some backends, this allows support
        # across backends.
        provider = getattr(self, 'override_provider', None) or self.provider
        can_stream = provider.can_stream()
        customizations = provider.get_customizations()
        should_stream = customizations.get('streaming', False)
        should_stream_result = can_stream and should_stream
        self.log.debug(f"Provider should_stream: {should_stream_result}")
        return should_stream_result

    def streaming_args(self, interrupt_handler=False):
        calback_handlers = [
            VerboseStreamingStdOutCallbackHandler(),
        ]
        if interrupt_handler:
            calback_handlers.append(self.interrupt_streaming_callback_handler)
        args = {
            'streaming': True,
            'callback_manager': CallbackManager(calback_handlers),
        }
        return args

    def make_llm(self, customizations=None):
        customizations = customizations or {}
        llm = self.provider.make_llm(customizations)
        return llm

    def set_model(self, model_name):
        self.model = model_name
        return self.provider.set_model(model_name)

    def new_conversation(self):
        self.parent_message_id = None
        self.conversation_id = None
        self.conversation_title_set = None
        self.message_clipboard = None

    def terminate_stream(self, _signal, _frame):
        self.log.info("Received signal to terminate stream")
        if self.streaming:
            self.streaming = False

    def switch_to_conversation(self, conversation_id, parent_message_id):
        self.conversation_id = conversation_id
        self.parent_message_id = parent_message_id

    def get_runtime_config(self):
        return ""

    def run_template_setup(self, template_name, substitutions=None):
        self.log.info(f"Setting up run of template: {template_name}")
        substitutions = substitutions or {}
        message, overrides = self.template_manager.build_message_from_template(template_name, substitutions)
        preset_name = None
        if 'request_overrides' in overrides and 'preset' in overrides['request_overrides']:
            preset_name = overrides['request_overrides'].pop('preset')
            success, llm, user_message = self.set_override_llm(preset_name)
            if success:
                self.log.info(f"Switching to preset '{preset_name}' for template: {template_name}")
            else:
                return success, llm, user_message
        return True, (message, preset_name, overrides), f"Set up of template run complete: {template_name}"

    def run_template_compiled(self, message, preset_name=None, overrides=None):
        overrides = overrides or {}
        self.log.info("Running template")
        response = self._ask(message, **overrides)
        if preset_name:
            self.set_override_llm()
        return response

    def run_template(self, template_name, substitutions=None):
        success, response, user_message = self.run_template_setup(template_name, substitutions)
        if not success:
            return success, response, user_message
        message, preset_name, overrides = response
        response = self.backend.run_template_compiled(message, preset_name, overrides)
        return response

    @abstractmethod
    def conversation_data_to_messages(self, conversation_data):
        pass

    @abstractmethod
    def delete_conversation(self, uuid=None):
        pass

    @abstractmethod
    def set_title(self, title, conversation_id=None):
        pass

    @abstractmethod
    def get_history(self, limit=20, offset=0):
        pass

    @abstractmethod
    def get_conversation(self, uuid=None):
        pass

    @abstractmethod
    def set_override_llm(self, preset_name=None):
        pass

    @abstractmethod
    def ask_stream(self, prompt: str):
        pass

    @abstractmethod
    def ask(self, message: str):
        pass
