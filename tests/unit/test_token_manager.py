import pytest

from lwe.core.function_manager import FunctionManager
from lwe.core.function_cache import FunctionCache
from lwe.core.token_manager import TokenManager
from lwe.core.plugin_manager import PluginManager
from lwe.core.provider_manager import ProviderManager
from ..base import test_config, FakeBackend  # noqa: F401


@pytest.fixture
def function_manager(test_config):  # noqa: F811
    function_manager = FunctionManager(config=test_config)
    return function_manager


@pytest.fixture
def function_cache(test_config, function_manager):  # noqa: F811
    function_cache = FunctionCache(
        test_config,
        function_manager,
    )
    return function_cache


def make_token_manager(test_config, function_cache, provider=None, model_name=None):  # noqa: F811
    if not provider:
        backend = FakeBackend(test_config)
        plugin_manager = PluginManager(test_config, backend, additional_plugins=['provider_chat_openai'])
        provider_manager = ProviderManager(test_config, plugin_manager)
        success, provider, user_message = provider_manager.load_provider('provider_chat_openai')
        if not success:
            raise Exception(user_message)
        provider.setup()
    if not model_name:
        model_name = getattr(provider.make_llm(), provider.model_property_name)
    token_manager = TokenManager(
        test_config,
        provider,
        model_name,
        function_cache,
    )
    return token_manager


def test_get_token_encoding(test_config, function_cache):  # noqa: F811
    token_manager = make_token_manager(test_config, function_cache)
    encoding = token_manager.get_token_encoding()
    assert encoding is not None


def test_get_token_encoding_unsupported_model(test_config, function_cache):  # noqa: F811
    token_manager = make_token_manager(test_config, function_cache, model_name="unsupported_model")
    with pytest.raises(NotImplementedError):
        token_manager.get_token_encoding()


def test_get_num_tokens_from_messages(test_config, function_cache):  # noqa: F811
    token_manager = make_token_manager(test_config, function_cache)
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


def test_get_num_tokens_from_messages_with_function(test_config, function_cache):  # noqa: F811
    token_manager = make_token_manager(test_config, function_cache)
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
            "message": {
                "arguments": {"repeats": 2, "word": "foo"},
                "name": "test_function",
            },
            "message_metadata": None,
            "message_type": "function_call",
            "role": "assistant",
        },
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_function"},
            "message_type": "function_response",
            "role": "function",
        },
        {
            "message": 'The word "foo" repeated twice is "foo foo".',
            "message_metadata": None,
            "message_type": "content",
            "role": "assistant",
        },
    ]
    num_tokens = token_manager.get_num_tokens_from_messages(messages)
    assert num_tokens == 253
