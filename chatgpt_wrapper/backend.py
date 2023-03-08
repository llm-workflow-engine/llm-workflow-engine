from abc import ABC, abstractmethod

import platform
import signal

import chatgpt_wrapper.constants as constants
from chatgpt_wrapper.config import Config
from chatgpt_wrapper.logger import Logger
import chatgpt_wrapper.debug as debug
if False:
    debug.console(None)

from rich.console import Console

is_windows = platform.system() == "Windows"

class Backend(ABC):
    """
    Base class/interface for all backends.
    """

    def __init__(self, config=None):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.parent_message_id = None
        self.conversation_id = None
        self.conversation_title_set = None
        self.model = constants.OPENAPI_CHAT_RENDER_MODELS[self.config.get('chat.model')]
        self.streaming = False
        self._setup_signal_handlers()
        self.console = Console()

    def _setup_signal_handlers(self):
        sig = is_windows and signal.SIGBREAK or signal.SIGUSR1
        signal.signal(sig, self.terminate_stream)

    def _print_status_message(self, success, message):
        self.console.print(message, style="bold green" if success else "bold red")
        print("")

    def new_conversation(self):
        self.parent_message_id = None
        self.conversation_id = None
        self.conversation_title_set = None

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
    async def ask(self, message: str) -> str:
        pass
