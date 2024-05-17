import pytest

from lwe.core.tool_cache import ToolCache


def make_tool_cache(test_config, tool_manager, customizations=None):
    customizations = customizations or {}
    tool_cache = ToolCache(
        test_config,
        tool_manager,
        customizations=customizations,
    )
    return tool_cache


def test_tool_cache_init(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    assert tool_cache.config == test_config
    assert tool_cache.tool_manager == tool_manager
    assert tool_cache.customizations == {}
    assert tool_cache.tools == []


def test_tool_cache_init_with_customizations(test_config, tool_manager):
    customizations = {"tools": ["test_tool"]}
    tool_cache = make_tool_cache(test_config, tool_manager, customizations)
    assert tool_cache.customizations == customizations
    assert "test_tool" in tool_cache.tools


def test_tool_cache_add_valid(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    tool_manager.tools = {"test_tool": "test_tool_path"}
    assert tool_cache.add("test_tool") is True
    assert "test_tool" in tool_cache.tools
    assert len(tool_cache.tools) == 1


def test_tool_cache_add_valid_only_adds_tool_once(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    tool_manager.tools = {"test_tool": "test_tool_path"}
    assert tool_cache.add("test_tool") is True
    assert "test_tool" in tool_cache.tools
    assert len(tool_cache.tools) == 1
    assert tool_cache.add("test_tool") is True
    assert len(tool_cache.tools) == 1


def test_tool_cache_add_valid_from_customizations(test_config, tool_manager):
    customizations = {"tools": ["test_tool"]}
    tool_manager.tools = {"test_tool": "test_tool_path"}
    tool_cache = make_tool_cache(test_config, tool_manager, customizations)
    assert "test_tool" in tool_cache.tools
    assert len(tool_cache.tools) == 1


def test_tool_cache_add_skip_non_string_tool_definition_from_customizations(
    test_config, tool_manager
):
    customizations = {"tools": dict()}
    tool_cache = make_tool_cache(test_config, tool_manager, customizations)
    assert len(tool_cache.tools) == 0


def test_tool_cache_add_bad_tool(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    tool_manager.tools = {}
    with pytest.raises(ValueError) as excinfo:
        tool_cache.add("test_tool")
    assert "test_tool not found" in str(excinfo.value)


def test_tool_cache_add_valid_langchain_tool(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    tool_manager.tools = {"Langchain-MoveFileTool": "test_tool_path"}
    assert tool_cache.add("Langchain-MoveFileTool") is True
    assert "Langchain-MoveFileTool" in tool_cache.tools
    assert len(tool_cache.tools) == 1


def test_tool_cache_add_bad_langchain_tool(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    tool_manager.tools = {"Langchain-BadTool": "test_tool_path"}
    with pytest.raises(ValueError) as excinfo:
        tool_cache.add("Langchain-BadTool")
    assert "Langchain-BadTool not found" in str(excinfo.value)


def test_tool_cache_add_message_tools(test_config, tool_manager):
    tool_cache = make_tool_cache(test_config, tool_manager)
    messages = [
        {"message_type": "tool_call", "message": [{"name": "test_tool"}]},
        {"message_type": "tool_response", "message_metadata": {"name": "test_tool"}},
        {"message_type": "content", "message": "test"},
        {"message_type": "tool_call", "message": [{"name": "missing_tool"}]},
    ]
    tool_manager.tools = {"test_tool": "test_tool_path"}
    filtered_messages = tool_cache.add_message_tools(messages)
    assert len(filtered_messages) == 3
    assert "test_tool" in tool_cache.tools
