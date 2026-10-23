"""Configure third-party Chat Completions models through OpenAI compatibility."""

from __future__ import annotations

import os
from typing import Any
from pydantic import Field

from langchain_openai import ChatOpenAI

from lwe.core.provider import Provider, PresetValue


class CustomChatOpenAICompat(ChatOpenAI):

    api_key_env_var: str | None = Field(default=None)
    """Name of the environment variable storing the OpenAI API key."""

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "chat_openai_compat"

    def __init__(self, **kwargs: Any) -> None:
        """Resolve explicitly selected credentials without falling back silently."""
        api_key_env_var = kwargs.pop("api_key_env_var", None)
        if api_key_env_var:
            api_key = os.getenv(api_key_env_var)
            if not api_key:
                raise ValueError(
                    f"Missing API key environment variable: {api_key_env_var}"
                )
            kwargs.pop("api_key", None)
            kwargs["openai_api_key"] = api_key
        super().__init__(**kwargs)


class ProviderChatOpenaiCompat(Provider):
    """
    Access to third-party chat models via an OpenAI compatible API
    """

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "chat": True,
            "validate_models": False,
            "models": {},
        }

    @property
    def default_model(self) -> None:
        return None

    def prepare_messages_method(self):
        return self.prepare_messages_for_llm_chat

    def llm_factory(self) -> type[CustomChatOpenAICompat]:
        return CustomChatOpenAICompat

    def default_customizations(
        self, defaults: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Read model defaults without requiring credentials before preset loading.

        The temporary key is discarded; actual clients still resolve credentials
        from the preset or the usual environment variable.
        """
        defaults = dict(defaults or {})
        temporary_key = not any(
            key in defaults for key in ("api_key_env_var", "openai_api_key", "api_key")
        )
        if temporary_key:
            defaults["openai_api_key"] = "lwe-defaults-only"
        customizations = super().default_customizations(defaults)
        if temporary_key:
            customizations.pop("openai_api_key", None)
        return customizations

    def customization_config(self) -> dict[str, Any]:
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
            "reasoning_effort": PresetValue(str, include_none=True),
            "use_responses_api": PresetValue(bool, include_none=True),
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
                "modalities": None,
                "response_format": dict,
                "user": PresetValue(str),
            },
        }
