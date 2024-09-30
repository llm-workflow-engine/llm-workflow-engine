import pytest

from lwe.core.token_manager import TokenManager
from ..base import make_provider


def make_token_manager(test_config, tool_cache, provider_manager, provider=None, model_name=None):
    if not provider:
        provider = make_provider(provider_manager)
    if not model_name:
        model_name = getattr(provider.make_llm(), provider.model_property_name)
    token_manager = TokenManager(
        test_config,
        provider,
        model_name,
        tool_cache,
    )
    return token_manager


def test_get_token_encoding(test_config, tool_cache, provider_manager):
    token_manager = make_token_manager(test_config, tool_cache, provider_manager)
    encoding = token_manager.get_token_encoding()
    assert encoding is not None


def test_get_token_encoding_unsupported_model(test_config, tool_cache, provider_manager):
    provider = make_provider(provider_manager)
    # Monkey patch provider_fake_llm to validate models.
    capabilities = provider.capabilities
    capabilities["validate_models"] = True
    provider.capabilities = capabilities
    token_manager = make_token_manager(
        test_config, tool_cache, provider_manager, provider, model_name="unsupported_model"
    )
    with pytest.raises(NotImplementedError):
        token_manager.get_token_encoding()


def test_get_num_tokens_from_messages(test_config, tool_cache, provider_manager):
    token_manager = make_token_manager(test_config, tool_cache, provider_manager)
    messages = [
        {
            "message": "You are a helpful assistant.",
            "message_metadata": None,
            "message_type": "content",
            "role": "system",
        },
        {
            "message": "Say one word hello.",
            "message_metadata": None,
            "message_type": "content",
            "role": "user",
        },
        {
            "message": "Hello.",
            "message_metadata": None,
            "message_type": "content",
            "role": "assistant",
        },
    ]
    num_tokens = token_manager.get_num_tokens_from_messages(messages)
    assert num_tokens == 30


def test_get_num_tokens_from_messages_with_tool(test_config, tool_cache, provider_manager):
    token_manager = make_token_manager(test_config, tool_cache, provider_manager)
    messages = [
        {
            "message": "You are a helpful assistant.",
            "message_metadata": None,
            "message_type": "content",
            "role": "system",
        },
        {
            "message": "Repeat the word foo twice",
            "message_metadata": None,
            "message_type": "content",
            "role": "user",
        },
        {
            "message": [
                {
                    "name": "test_tool",
                    "args": {
                        "word": "foo",
                        "repeats": 2,
                    },
                    "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                },
            ],
            "message_metadata": None,
            "message_type": "tool_call",
            "role": "assistant",
        },
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_tool", "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"},
            "message_type": "tool_response",
            "role": "tool",
        },
        {
            "message": 'The word "foo" repeated twice is "foo foo".',
            "message_metadata": None,
            "message_type": "content",
            "role": "assistant",
        },
    ]
    num_tokens = token_manager.get_num_tokens_from_messages(messages)
    assert num_tokens == 381
