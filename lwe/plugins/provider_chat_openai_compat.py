import os

from typing import Optional
from pydantic import Field

from langchain_openai import ChatOpenAI

from lwe.core.provider import Provider, PresetValue


class CustomChatOpenAICompat(ChatOpenAI):

    api_key_env_var: Optional[str] = Field(default=None)
    """Name of the environment variable storing the OpenAI API key."""

    @property
    def _llm_type(self):
        """Return type of llm."""
        return "chat_openai_compat"

    def __init__(self, **kwargs):
        openai_api_key = None
        if 'api_key_env_var' in kwargs:
            openai_api_key = os.getenv(kwargs.pop('api_key_env_var'))
        elif 'openai_api_key' in kwargs:
            openai_api_key = kwargs.pop('openai_api_key')
        if openai_api_key is not None:
            super().__init__(openai_api_key=openai_api_key, **kwargs)
        else:
            super().__init__(**kwargs)


class ProviderChatOpenaiCompat(Provider):
    """
    Access to third-party chat models via an OpenAI compatible API
    """

    @property
    def capabilities(self):
        return {
            "chat": True,
            "validate_models": False,
            "models": {},
        }

    @property
    def default_model(self):
        pass

    def prepare_messages_method(self):
        return self.prepare_messages_for_llm_chat

    def llm_factory(self):
        return CustomChatOpenAICompat

    def customization_config(self):
        return {
            "verbose": PresetValue(bool),
            "model_name": PresetValue(str, options=self.available_models),
            "temperature": PresetValue(float, min_value=0.0, max_value=2.0),
            "openai_api_base": PresetValue(str, include_none=True),
            "api_key_env_var": PresetValue(str, include_none=True),
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
