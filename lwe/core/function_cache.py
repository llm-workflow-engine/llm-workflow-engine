from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util


class FunctionCache:
    """Manage functions in a cache."""

    def __init__(self, config, function_manager, customizations=None):
        """Initialize the function cache."""
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.function_manager = function_manager
        self.customizations = customizations or {}
        success, _functions, user_message = self.function_manager.load_functions()
        if not success:
            raise RuntimeError(user_message)
        self.functions = []
        self.add_customizations_functions()

    def add_customizations_functions(self):
        if self.customizations:
            if (
                "model_kwargs" in self.customizations
                and "functions" in self.customizations["model_kwargs"]
            ):
                for function_name in self.customizations["model_kwargs"]["functions"]:
                    if isinstance(function_name, str):
                        self.add(function_name)

    def add(self, function_name, raise_on_missing=True):
        """Add a function to the cache if valid."""
        if self.function_manager.is_langchain_tool(function_name):
            if not self.function_manager.get_langchain_tool(function_name):
                if raise_on_missing:
                    raise ValueError(f"Langchain function {function_name} not found")
                else:
                    return False
        else:
            if function_name not in self.function_manager.functions:
                if raise_on_missing:
                    raise ValueError(f"Function {function_name} not found")
                else:
                    return False
        if function_name not in self.functions:
            self.functions.append(function_name)
        return True

    def add_message_functions(self, messages):
        """Add any function calls in messages to cache."""
        filtered_messages = []
        for message in messages:
            m_type = message["message_type"]
            if m_type in ["function_call", "function_response"]:
                if m_type == "function_call":
                    function_name = message["message"]["name"]
                elif m_type == "function_response":
                    function_name = message["message_metadata"]["name"]
                if self.add(function_name, raise_on_missing=False):
                    filtered_messages.append(message)
                else:
                    message = (
                        f"Function {function_name} not found in function list, filtered message out"
                    )
                    self.log.warning(message)
                    util.print_status_message(False, message)
            else:
                filtered_messages.append(message)
        return filtered_messages
