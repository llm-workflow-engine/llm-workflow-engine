from abc import ABC, abstractmethod
from typing import Any

from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger
from chatgpt_wrapper.core import util

class VerboseStreamingStdOutCallbackHandler(StreamingStdOutCallbackHandler):
    @property
    def always_verbose(self) -> bool:
        """Whether to call verbose callbacks even if verbose is False."""
        return True

def make_interrupt_streaming_callback_handler(backend):
    class InterruptStreamingCallbackHandler(VerboseStreamingStdOutCallbackHandler):
        def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
            if not backend.streaming:
                util.print_status_message(False, "\n\nWARNING:\nStream interruption on the API backend is not currently working properly, and may not properly store information on an interrupted stream.\nIf you'd like to help fix this error, see https://github.com/mmabrouk/chatgpt-wrapper/issues/274")
                message = "Request to interrupt streaming"
                backend.log.info(message)
                raise EOFError(message)
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
        self.set_available_models()
        self.set_active_model(self.config.get('chat.model') or self.default_model())

    def set_provider_streaming(self, stream=None):
        if self.provider.can_stream():
            if stream is not None:
                self.stream = stream
            self.provider.set_customization_value('streaming', self.stream)

    def streaming_args(self, interrupt_handler=False):
        calback_handlers = [
            VerboseStreamingStdOutCallbackHandler(),
        ]
        if interrupt_handler:
            calback_handlers.append(self.interrupt_streaming_callback_handler)
        args = {
            'callback_manager': CallbackManager(calback_handlers),
        }
        return args

    def make_llm(self, customizations={}):
        llm = self.provider.make_llm(customizations)
        return llm

    def set_model(self, model_name):
        self.model = model_name
        return self.provider.set_model(model_name)

    # TODO: This needs to die.
    def set_active_model(self, model=None):
        self.model = model

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

    @abstractmethod
    def default_model(self):
        pass

    @abstractmethod
    def set_available_models(self):
        pass

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
    def ask_stream(self, prompt: str):
        pass

    @abstractmethod
    def ask(self, message: str):
        pass
