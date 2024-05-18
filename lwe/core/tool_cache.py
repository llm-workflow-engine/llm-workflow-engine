from lwe.core.config import Config
from lwe.core.logger import Logger
import lwe.core.util as util


class ToolCache:
    """Manage tools in a cache."""

    def __init__(self, config, tool_manager, customizations=None):
        """Initialize the tool cache."""
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.tool_manager = tool_manager
        self.customizations = customizations or {}
        success, _tools, user_message = self.tool_manager.load_tools()
        if not success:
            raise RuntimeError(user_message)
        self.tools = []
        self.add_customizations_tools()

    def add_customizations_tools(self):
        if self.customizations:
            if "tools" in self.customizations:
                for tool_name in self.customizations["tools"]:
                    if isinstance(tool_name, str):
                        self.add(tool_name)

    def add(self, tool_name, raise_on_missing=True):
        """Add a tool to the cache if valid."""
        if self.tool_manager.is_langchain_tool(tool_name):
            if not self.tool_manager.get_langchain_tool(tool_name):
                if raise_on_missing:
                    raise ValueError(f"Langchain tool {tool_name} not found")
                else:
                    return False
        else:
            if tool_name not in self.tool_manager.tools:
                if raise_on_missing:
                    raise ValueError(f"Tool {tool_name} not found")
                else:
                    return False
        if tool_name not in self.tools:
            self.tools.append(tool_name)
        return True

    def add_message_tools(self, messages):
        """Add any tool calls in messages to cache."""
        filtered_messages = []
        for message in messages:
            m_type = message["message_type"]
            if m_type in ["tool_call", "tool_response"]:
                tool_names = []
                if m_type == "tool_call":
                    tool_names = [m["name"] for m in message["message"]]
                elif m_type == "tool_response":
                    tool_names = [message["message_metadata"]["name"]]
                for tool_name in tool_names:
                    if self.add(tool_name, raise_on_missing=False):
                        filtered_messages.append(message)
                    else:
                        message = f"Tool {tool_name} not found in tool list, filtered message out"
                        self.log.warning(message)
                        util.print_status_message(False, message)
            else:
                filtered_messages.append(message)
        return filtered_messages
