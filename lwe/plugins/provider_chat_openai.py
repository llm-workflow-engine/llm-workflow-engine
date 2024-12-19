from langchain_openai import ChatOpenAI

from lwe.core.provider import Provider, PresetValue
from lwe.core import constants


class CustomChatOpenAI(ChatOpenAI):
    @property
    def _llm_type(self):
        """Return type of llm."""
        return "chat_openai"


class ProviderChatOpenai(Provider):
    """
    Access to OpenAI chat models via the OpenAI API
    """

    @property
    def capabilities(self):
        return {
            "chat": True,
        }

    @property
    def default_model(self):
        return constants.API_BACKEND_DEFAULT_MODEL

    @property
    def static_models(self):
        return {
            "gpt-3.5-turbo": {
                "max_tokens": 16384,
            },
            "gpt-3.5-turbo-16k": {
                "max_tokens": 16384,
            },
            "gpt-3.5-turbo-0613": {
                "max_tokens": 4096,
            },
            "gpt-3.5-turbo-16k-0613": {
                "max_tokens": 16384,
            },
            "gpt-3.5-turbo-1106": {
                "max_tokens": 16384,
            },
            "gpt-3.5-turbo-0125": {
                "max_tokens": 16384,
            },
            "gpt-4": {
                "max_tokens": 8192,
            },
            "gpt-4-32k": {
                "max_tokens": 32768,
            },
            "gpt-4-0613": {
                "max_tokens": 8192,
            },
            "gpt-4-32k-0613": {
                "max_tokens": 32768,
            },
            "gpt-4-turbo": {
                "max_tokens": 131072,
            },
            "gpt-4-turbo-2024-04-09": {
                "max_tokens": 131072,
            },
            "gpt-4-turbo-preview": {
                "max_tokens": 131072,
            },
            "gpt-4-1106-preview": {
                "max_tokens": 131072,
            },
            "gpt-4-0125-preview": {
                "max_tokens": 131072,
            },
            "gpt-4o": {
                "max_tokens": 131072,
            },
            "chatgpt-4o-latest": {
                "max_tokens": 131072,
            },
            "gpt-4o-2024-05-13": {
                "max_tokens": 131072,
            },
            "gpt-4o-2024-08-06": {
                "max_tokens": 131072,
            },
            "gpt-4o-2024-11-20": {
                "max_tokens": 131072,
            },
            "gpt-4o-mini": {
                "max_tokens": 131072,
            },
            "gpt-4o-mini-2024-07-18": {
                "max_tokens": 131072,
            },
            "o1-preview": {
                "max_tokens": 131072,
            },
            "o1-preview-2024-09-12": {
                "max_tokens": 131072,
            },
            "o1-mini": {
                "max_tokens": 131072,
            },
            "o1-mini-2024-09-12": {
                "max_tokens": 131072,
            },
            "o1": {
                "max_tokens": 204800,
            },
            "o1-2024-12-17": {
                "max_tokens": 204800,
            },
        }

    def prepare_messages_method(self):
        return self.prepare_messages_for_llm_chat

    def llm_factory(self):
        return CustomChatOpenAI

    def customization_config(self):
        return {
            "verbose": PresetValue(bool),
            "model_name": PresetValue(str, options=self.available_models),
            "temperature": PresetValue(float, min_value=0.0, max_value=2.0),
            "openai_api_base": PresetValue(str, include_none=True),
            "openai_api_key": PresetValue(str, include_none=True, private=True),
            "openai_organization": PresetValue(str, include_none=True, private=True),
            "request_timeout": PresetValue(int),
            "max_retries": PresetValue(int, 1, 10),
            "n": PresetValue(int, 1, 10),
            "max_tokens": PresetValue(int, include_none=True),
            "top_p": PresetValue(float, min_value=0.0, max_value=1.0),
            "presence_penalty": PresetValue(float, min_value=-2.0, max_value=2.0),
            "frequency_penalty": PresetValue(float, min_value=-2.0, max_value=2.0),
            "seed": PresetValue(int, include_none=True),
            "logprobs": PresetValue(bool, include_none=True),
            "top_logprobs": PresetValue(int, min_value=0, max_value=20, include_none=True),
            "logit_bias": dict,
            "stop": PresetValue(str, include_none=True),
            "tools": None,
            "tool_choice": None,
            "model_kwargs": {
                "response_format": dict,
                "user": PresetValue(str),
            },
        }
