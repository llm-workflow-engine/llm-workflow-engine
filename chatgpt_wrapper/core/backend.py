from abc import ABC, abstractmethod

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.core.logger import Logger

class Backend(ABC):
    """
    Base class/interface for all backends.
    """

    def __init__(self, config=None):
        self.name = self.get_backend_name()
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.parent_message_id = None
        self.conversation_id = None
        self.conversation_title_set = None
        self.message_clipboard = None
        self.streaming = False
        self.set_available_models()
        self.set_active_model(self.config.get('chat.model'))

    def set_active_model(self, model=None):
        if model is None:
            self.model = None
        else:
            self.model = self.available_models[model]

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
    def get_backend_name(self):
        pass

    @abstractmethod
    def set_available_models(self):
        raise NotImplementedError

    @abstractmethod
    def conversation_data_to_messages(self, conversation_data):
        pass

    @abstractmethod
    async def delete_conversation(self, uuid=None):
        pass

    @abstractmethod
    async def set_title(self, title, conversation_id=None):
        pass

    @abstractmethod
    async def get_history(self, limit=20, offset=0):
        pass

    @abstractmethod
    async def get_conversation(self, uuid=None):
        pass

    @abstractmethod
    async def ask_stream(self, prompt: str):
        pass

    @abstractmethod
    async def ask(self, message: str):
        pass
