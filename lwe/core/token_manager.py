import json
import tiktoken

from lwe.core.config import Config
from lwe.core.logger import Logger

from lwe.core import util


class TokenManager:
    """Manage model tokens."""

    def __init__(self, config, provider, model_name, tool_cache):
        self.config = config or Config()
        self.log = Logger(self.__class__.__name__, self.config)
        self.provider = provider
        self.model_name = model_name
        self.tool_cache = tool_cache

    def get_token_encoding(self):
        """
        Get token encoding for a model.

        :raises NotImplementedError: If unsupported model
        :raises Exception: If error getting encoding
        :returns: Encoding object
        :rtype: Encoding
        """
        validate_models = self.provider.get_capability("validate_models", True)
        if validate_models and self.model_name not in self.provider.available_models:
            raise NotImplementedError(f"Unsupported model: {self.model_name}")
        try:
            encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as err:
            raise Exception(
                f"Unable to get token encoding for model {self.model_name}: {str(err)}"
            ) from err
        return encoding

    def get_num_tokens_from_messages(self, messages, encoding=None):
        """
        Get number of tokens for a list of messages.

        If a provider does not have a get num_tokens_from_messages() method,
        default_get_num_tokens_from_messages() will be used.

        :param messages: List of messages
        :type messages: list
        :param encoding: Encoding to use, defaults to None to auto-detect
        :type encoding: Encoding, optional
        :returns: Number of tokens
        :rtype: int
        """
        token_counter = getattr(self.provider, "get_num_tokens_from_messages", None)
        return (
            token_counter(messages, encoding)
            if token_counter
            else self.default_get_num_tokens_from_messages(messages, encoding)
        )

    def default_get_num_tokens_from_messages(self, messages, encoding=None):
        """
        Get number of tokens for a list of messages.

        The default implementation uses tiktoken, which is the OpenAI implementation.

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
        messages = self.tool_cache.add_message_tools(messages)
        messages = util.transform_messages_to_chat_messages(messages)
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                if isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value, indent=2)
                if value:
                    num_tokens += len(encoding.encode(str(value)))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        if len(self.tool_cache.tools) > 0:
            tools = [
                self.tool_cache.tool_manager.get_tool_config(tool_name)
                for tool_name in self.tool_cache.tools
            ]
            tools_string = json.dumps(tools, indent=2)
            num_tokens += len(encoding.encode(tools_string))
        return num_tokens
