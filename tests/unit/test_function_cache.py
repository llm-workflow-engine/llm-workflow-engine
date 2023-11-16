import pytest

from lwe.core.function_cache import FunctionCache


def make_function_cache(test_config, function_manager, customizations=None):
    customizations = customizations or {}
    function_cache = FunctionCache(
        test_config,
        function_manager,
        customizations=customizations,
    )
    return function_cache


def test_function_cache_init(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    assert function_cache.config == test_config
    assert function_cache.function_manager == function_manager
    assert function_cache.customizations == {}
    assert function_cache.functions == []


def test_function_cache_init_with_customizations(test_config, function_manager):
    customizations = {"model_kwargs": {"functions": ["test_function"]}}
    function_cache = make_function_cache(test_config, function_manager, customizations)
    assert function_cache.customizations == customizations
    assert "test_function" in function_cache.functions


def test_function_cache_add_valid(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    function_manager.functions = {"test_function": "test_function_path"}
    assert function_cache.add("test_function") is True
    assert "test_function" in function_cache.functions
    assert len(function_cache.functions) == 1


def test_function_cache_add_valid_only_adds_function_once(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    function_manager.functions = {"test_function": "test_function_path"}
    assert function_cache.add("test_function") is True
    assert "test_function" in function_cache.functions
    assert len(function_cache.functions) == 1
    assert function_cache.add("test_function") is True
    assert len(function_cache.functions) == 1


def test_function_cache_add_valid_from_customizations(test_config, function_manager):
    customizations = {"model_kwargs": {"functions": ["test_function"]}}
    function_manager.functions = {"test_function": "test_function_path"}
    function_cache = make_function_cache(test_config, function_manager, customizations)
    assert "test_function" in function_cache.functions
    assert len(function_cache.functions) == 1


def test_function_cache_add_skip_non_string_function_definition_from_customizations(
    test_config, function_manager
):
    customizations = {"model_kwargs": {"functions": dict()}}
    function_cache = make_function_cache(test_config, function_manager, customizations)
    assert len(function_cache.functions) == 0


def test_function_cache_add_bad_function(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    function_manager.functions = {}
    with pytest.raises(ValueError) as excinfo:
        function_cache.add("test_function")
    assert "test_function not found" in str(excinfo.value)


def test_function_cache_add_valid_langchain_tool(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    function_manager.functions = {"Langchain-MoveFileTool": "test_function_path"}
    assert function_cache.add("Langchain-MoveFileTool") is True
    assert "Langchain-MoveFileTool" in function_cache.functions
    assert len(function_cache.functions) == 1


def test_function_cache_add_bad_langchain_tool(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    function_manager.functions = {"Langchain-BadTool": "test_function_path"}
    with pytest.raises(ValueError) as excinfo:
        function_cache.add("Langchain-BadTool")
    assert "Langchain-BadTool not found" in str(excinfo.value)


def test_function_cache_add_message_functions(test_config, function_manager):
    function_cache = make_function_cache(test_config, function_manager)
    messages = [
        {"message_type": "function_call", "message": {"name": "test_function"}},
        {"message_type": "function_response", "message_metadata": {"name": "test_function"}},
        {"message_type": "content", "message": "test"},
        {"message_type": "function_call", "message": {"name": "missing_function"}},
    ]
    function_manager.functions = {"test_function": "test_function_path"}
    filtered_messages = function_cache.add_message_functions(messages)
    assert len(filtered_messages) == 3
    assert "test_function" in function_cache.functions
