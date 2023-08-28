import pytest

from lwe.core.function_manager import FunctionManager
from lwe.core.function_cache import FunctionCache
from ..base import test_config  # noqa: F401


@pytest.fixture
def function_manager(test_config):  # noqa: F811
    function_manager = FunctionManager(config=test_config)
    return function_manager


def make_function_cache(function_manager, customizations=None):
    customizations = customizations or {}
    function_cache = FunctionCache(
        test_config,
        function_manager,
        customizations=customizations,
    )
    return function_cache


def test_function_cache_init(function_manager):
    function_cache = make_function_cache(function_manager)
    assert function_cache.config == test_config
    assert function_cache.function_manager == function_manager
    assert function_cache.customizations == {}
    assert function_cache.functions == []


def test_function_cache_init_with_customizations(function_manager):
    customizations = {'model_kwargs': {'functions': ['test_function']}}
    function_cache = make_function_cache(function_manager, customizations)
    assert function_cache.customizations == customizations
    assert 'test_function' in function_cache.functions


def test_function_cache_add(function_manager):
    function_cache = make_function_cache(function_manager)
    function_manager.functions = {}
    assert function_cache.add('test_function') is False
    assert len(function_cache.functions) == 0
    function_manager.functions = {'test_function': 'test_function_path'}
    assert function_cache.add('test_function') is True
    assert 'test_function' in function_cache.functions
    assert len(function_cache.functions) == 1
    assert function_cache.add('test_function') is True
    assert len(function_cache.functions) == 1


def test_function_cache_add_langchain_tool(function_manager):
    function_cache = make_function_cache(function_manager)
    function_manager.functions = {'Langchain-BadTool': 'test_function_path'}
    assert function_cache.add('Langchain-BadTool') is False
    assert len(function_cache.functions) == 0
    function_manager.functions = {'Langchain-ShellTool': 'test_function_path'}
    assert function_cache.add('Langchain-ShellTool') is True
    assert 'Langchain-ShellTool' in function_cache.functions
    assert len(function_cache.functions) == 1


def test_function_cache_add_message_functions(function_manager):
    function_cache = make_function_cache(function_manager)
    messages = [
        {'message_type': 'function_call', 'message': {'name': 'test_function'}},
        {'message_type': 'function_response', 'message_metadata': {'name': 'test_function'}},
        {'message_type': 'content', 'message': 'test'},
        {'message_type': 'function_call', 'message': {'name': 'missing_function'}},
    ]
    function_manager.functions = {'test_function': 'test_function_path'}
    filtered_messages = function_cache.add_message_functions(messages)
    assert len(filtered_messages) == 3
    assert 'test_function' in function_cache.functions
