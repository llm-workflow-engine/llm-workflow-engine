"""Verify compatibility-provider presets and credentials without model calls."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import HumanMessage

from lwe.plugins.provider_chat_openai_compat import (
    CustomChatOpenAICompat,
    ProviderChatOpenaiCompat,
)


class TestProviderChatOpenaiCompat:
    """Exercise schema validation and the serialized Chat Completions payload."""

    @pytest.fixture
    def provider(self) -> ProviderChatOpenaiCompat:
        """Construct only the provider state required for customization handling."""
        provider = object.__new__(ProviderChatOpenaiCompat)
        provider.models = provider.static_models
        provider.set_customizations({})
        return provider

    @pytest.mark.parametrize(
        ("name", "value"),
        [("reasoning_effort", "none"), ("model_kwargs.modalities", ["text"]),
         ("use_responses_api", False)],
    )
    def test_preset_parameters_are_accepted(
        self, provider: ProviderChatOpenaiCompat, name: str, value: Any
    ) -> None:
        success, _, _ = provider.set_customization_value(name, value)
        assert success
        success, actual_value, _ = provider.get_customization_value(name)
        assert success
        assert actual_value == value

    def test_defaults_do_not_require_an_openai_key(
        self, provider: ProviderChatOpenaiCompat, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        defaults = provider.default_customizations()
        assert "openai_api_key" not in defaults

    def test_explicit_missing_key_does_not_use_openai_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "unrelated-key")
        monkeypatch.delenv("CUSTOM_API_KEY", raising=False)
        with pytest.raises(ValueError, match="CUSTOM_API_KEY"):
            CustomChatOpenAICompat(api_key_env_var="CUSTOM_API_KEY")

    def test_chat_completions_parameters_are_forwarded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("CUSTOM_API_KEY", "test-custom-key")
        llm = CustomChatOpenAICompat(
            model_name="custom-chat-model",
            openai_api_base="https://example.com/v1",
            api_key_env_var="CUSTOM_API_KEY",
            reasoning_effort="none",
            model_kwargs={"modalities": ["text"]},
            use_responses_api=False,
        )
        payload = llm._get_request_payload([HumanMessage(content="Hello")])
        assert payload["model"] == "custom-chat-model"
        assert payload["reasoning_effort"] == "none"
        assert payload["modalities"] == ["text"]
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]
        assert "input" not in payload
        assert llm.openai_api_key.get_secret_value() == "test-custom-key"
