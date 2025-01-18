import copy
import pytest

from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage

from lwe.core import constants
from lwe.core import util
from lwe.core.token_manager import TokenManager
from lwe.backends.api.request import ApiRequest  # noqa: F401
from ..base import (
    clean_output,
    make_provider,
    make_api_request,
    TEST_BASIC_MESSAGES,
    TEST_TOOL_CALL_RESPONSE_MESSAGES,
)


def test_init_with_defaults(test_config, tool_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider
    )
    assert request.config == test_config
    assert request.provider == provider
    assert request.provider_manager == provider_manager
    assert request.tool_manager == tool_manager
    assert request.input == "test"
    assert request.default_preset is None
    assert request.default_preset_name is None
    assert request.preset_manager == preset_manager


def test_init_with_request_overrides(test_config, tool_manager, provider_manager, preset_manager):
    request_overrides = {"stream": True}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    assert request.request_overrides == request_overrides


def test_init_with_preset(test_config, tool_manager, provider_manager, preset_manager):
    preset = preset_manager.presets["test"]
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, preset=preset
    )
    assert request.default_preset == preset
    assert request.default_preset_name == "test"


def test_set_request_llm_success(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    preset_name = "test"
    preset_overrides = {"metadata": {"key": "value"}}
    metadata = {"key": "value"}
    customizations = {"key": "value"}
    request.extract_metadata_customizations = Mock(
        return_value=(True, (preset_name, preset_overrides, metadata, customizations), "Success")
    )
    llm = Mock()
    request.setup_request_config = Mock(return_value=(True, llm, "Success"))
    success, response, user_message = request.set_request_llm()
    assert request.setup_request_config.call_args.args[0] == preset_name
    assert request.setup_request_config.call_args.args[1] == preset_overrides
    assert request.setup_request_config.call_args.args[2] == metadata
    assert request.setup_request_config.call_args.args[3] == customizations
    assert success is True
    assert response == llm
    assert user_message == "Success"


def test_set_request_llm_failure(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.extract_metadata_customizations = Mock(return_value=(False, None, "Error"))
    success, response, user_message = request.set_request_llm()
    assert success is False
    assert response is None
    assert user_message == "Error"


def test_setup_request_config_success(test_config, tool_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider
    )
    provider = Mock()
    preset = Mock()
    llm = Mock()
    token_manager = Mock()
    request.build_request_config = Mock(
        return_value=(
            True,
            (provider, preset, llm, "test", constants.API_BACKEND_DEFAULT_MODEL, token_manager),
            "Success",
        )
    )
    success, response, user_message = request.setup_request_config(
        "preset_name", {"key": "value"}, {"key": "value"}, {"key": "value"}
    )
    assert success is True
    assert response == (
        provider,
        preset,
        llm,
        "test",
        constants.API_BACKEND_DEFAULT_MODEL,
        token_manager,
    )
    assert request.llm == llm
    assert request.provider == provider
    assert request.token_manager == token_manager
    assert request.preset_name == "test"
    assert request.model_name == constants.API_BACKEND_DEFAULT_MODEL
    assert request.preset == preset


def test_setup_request_config_failure(test_config, tool_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider
    )
    request.build_request_config = Mock(return_value=(False, None, "Error"))
    success, response, user_message = request.setup_request_config(
        "preset_name", {"key": "value"}, {"key": "value"}, {"key": "value"}
    )
    assert success is False
    assert response is None


def test_build_request_config_success_no_preset_name(
    test_config, tool_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    provider.make_llm = Mock(return_value=Mock(model_name=constants.API_BACKEND_DEFAULT_MODEL))
    request.load_provider = Mock(return_value=(True, provider, "Success"))
    request.merge_preset_overrides = Mock(
        return_value={
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    request.expand_tools = Mock(return_value=({"key": "value"}, None, None))
    request.tool_cache = Mock()
    success, response, user_message = request.build_request_config(
        {
            "preset_name": None,
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    assert success is True
    assert response[0] == provider
    assert response[1] == ({"one": "two"}, {"three": "four"})
    assert response[2] == provider.make_llm.return_value
    assert response[3] == ""
    assert response[4] == constants.API_BACKEND_DEFAULT_MODEL
    assert isinstance(response[5], TokenManager)


def test_build_request_config_success_with_preset_name(
    test_config, tool_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider
    )
    provider.make_llm = Mock(return_value=Mock(model_name=constants.API_BACKEND_DEFAULT_MODEL))
    request.merge_preset_overrides = Mock(
        return_value={
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    request.expand_tools = Mock(return_value=({"key": "value"}, None, None))
    request.tool_cache = Mock()
    success, response, user_message = request.build_request_config(
        {
            "preset_name": "test",
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    assert success is True
    assert response[0] == provider
    assert response[1] == ({"one": "two"}, {"three": "four"})
    assert response[2] == provider.make_llm.return_value
    assert response[3] == ""
    assert response[4] == constants.API_BACKEND_DEFAULT_MODEL
    assert isinstance(response[5], TokenManager)


def test_build_request_config_failure(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.load_provider = Mock(return_value=(False, None, "Error"))
    success, response, user_message = request.build_request_config(
        {
            "preset_name": None,
            "metadata": {"key": "value"},
            "customizations": {"key": "value"},
            "preset_overrides": {"key": "value"},
        }
    )
    assert success is False
    assert response is None


def test_prepare_config(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    config = request.prepare_config(
        {
            "preset_name": None,
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    assert config == {
        "preset_name": None,
        "metadata": {"one": "two"},
        "customizations": {"three": "four"},
        "preset_overrides": {"five": "six"},
    }


def test_prepare_config_defaults(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    config = request.prepare_config(
        {"preset_name": None, "metadata": None, "customizations": None, "preset_overrides": None}
    )
    assert config == {
        "preset_name": None,
        "metadata": {},
        "customizations": {},
        "preset_overrides": {},
    }


def test_load_provider_with_provider_in_metadata(
    test_config, tool_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.provider_manager.load_provider = Mock(return_value=(True, provider, "Success"))
    config = {"metadata": {"provider": "test_provider"}}
    success, response, user_message = request.load_provider(config)
    assert success is True
    assert response == provider
    request.provider_manager.load_provider.assert_called_once_with("test_provider")


def test_load_provider_without_provider_in_metadata(
    test_config, tool_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider
    )
    request.provider_manager.load_provider = Mock()
    config = {"metadata": {}}
    success, response, user_message = request.load_provider(config)
    assert success is True
    assert response == provider
    request.provider_manager.load_provider.assert_not_called()


def test_merge_preset_overrides(test_config, tool_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider
    )
    config = request.merge_preset_overrides(
        {
            "metadata": {"key": "value"},
            "customizations": {"key": "value"},
            "preset_overrides": {
                "metadata": {"key1": "value1"},
                "model_customizations": {"key2": "value2"},
            },
        }
    )
    assert config == {
        "metadata": {"key": "value", "key1": "value1"},
        "customizations": {"key": "value", "key2": "value2"},
        "preset_overrides": {
            "metadata": {"key1": "value1"},
            "model_customizations": {"key2": "value2"},
        },
    }


def test_extract_metadata_customizations_with_preset_name(
    test_config, tool_manager, provider_manager, preset_manager
):
    request_overrides = {"preset": "test_preset"}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    preset_manager.ensure_preset = Mock(
        return_value=(
            True,
            ({"name": "default_preset", "provider": "test_provider"}, {"key": "value"}),
            "user_message",
        )
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert success
    assert response == (
        "test_preset",
        None,
        {"name": "default_preset", "provider": "test_provider"},
        {"key": "value"},
    )


def test_extract_metadata_customizations_with_default_preset(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        preset=({"name": "default_preset", "provider": "test_provider"}, {"key": "value"}),
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert success
    assert response == (
        None,
        None,
        {"name": "default_preset", "provider": "test_provider"},
        request.provider.get_customizations(),
    )


def test_extract_metadata_customizations_with_preset_overrides(
    test_config, tool_manager, provider_manager, preset_manager
):
    request_overrides = {"preset": "test_preset", "preset_overrides": {"key": "value"}}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    preset_manager.ensure_preset = Mock(
        return_value=(
            True,
            ({"name": "default_preset", "provider": "test_provider"}, {"key1": "value1"}),
            "user_message",
        )
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert success
    assert response == (
        "test_preset",
        {"key": "value"},
        {"name": "default_preset", "provider": "test_provider"},
        {"key1": "value1"},
    )


def test_extract_metadata_customizations_with_provider(
    test_config, tool_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    provider.get_customizations = Mock(return_value={"key": "value"})
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, provider=provider
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert success
    assert response == (None, None, {"provider": provider.name}, {"key": "value"})


def test_extract_metadata_customizations_with_invalid_request_overrides(
    test_config, tool_manager, provider_manager, preset_manager
):
    request_overrides = {"preset_overrides": {"key": "value"}}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert not success
    assert response == (None, None, False)


def test_extract_metadata_customizations_with_failed_preset_ensuring(
    test_config, tool_manager, provider_manager, preset_manager
):
    request_overrides = {"preset": "test_preset"}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    preset_manager.ensure_preset = Mock(return_value=(False, "error", "user_message"))
    success, response, user_message = request.extract_metadata_customizations()
    assert not success
    assert response == "error"
    assert user_message == "user_message"


def test_get_preset_metadata_customizations(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    preset_manager.ensure_preset = Mock(
        return_value=(
            True,
            ({"name": "default_preset", "provider": "test_provider"}, {"key": "value"}),
            "user_message",
        )
    )
    success, response, user_message = request.get_preset_metadata_customizations("test_preset")
    assert success
    assert response == ({"name": "default_preset", "provider": "test_provider"}, {"key": "value"})


def test_get_preset_metadata_customizations_with_failed_preset_ensuring(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    preset_manager.ensure_preset = Mock(return_value=(False, "error", "user_message"))
    success, response, user_message = request.get_preset_metadata_customizations("test_preset")
    assert not success
    assert response == "error"
    assert user_message == "user_message"


def test_expand_tools_none(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    customizations = {}
    result, tools, tool_choice = request.expand_tools(customizations)
    assert result == {}
    assert tools == []
    assert tool_choice is None


def test_expand_tools_valid_tools(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tools_expanded = ["tool_config1", "tool_config2"]
    tool_choice_expanded = "test_tool_2"
    tool_manager.get_tool_config = Mock(side_effect=tools_expanded)
    customizations = {"tools": ["test_tool", "test_tool2"], "tool_choice": tool_choice_expanded}
    result, tools, tool_choice = request.expand_tools(customizations)
    assert result == {}
    assert tools == tools_expanded
    assert tool_choice == tool_choice_expanded


def test_expand_tools_missing_tool(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    customizations = {"tools": ["test_missing_tool"]}
    with pytest.raises(ValueError) as excinfo:
        request.expand_tools(customizations)
    assert "test_missing_tool not found" in str(excinfo.value)


def test_prepare_default_new_conversation_messages_no_old_messages_system_message_default(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.old_messages = []
    request.input = "test message"
    result = request.prepare_default_new_conversation_messages()
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["message"] == constants.SYSTEM_MESSAGE_DEFAULT
    assert result[1]["role"] == "user"
    assert result[1]["message"] == "test message"


def test_prepare_default_new_conversation_messages_no_old_messages_system_message_override(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.old_messages = []
    request.input = "test message"
    request.request_overrides["system_message"] = "test system message"
    result = request.prepare_default_new_conversation_messages()
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["message"] == "test system message"
    assert result[1]["role"] == "user"
    assert result[1]["message"] == "test message"


def test_prepare_default_new_conversation_messages_old_messages(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.old_messages = TEST_BASIC_MESSAGES
    request.input = "test message"
    result = request.prepare_default_new_conversation_messages()
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["message"] == "test message"


def test_prepare_custom_new_conversation_messages(
    test_config, tool_manager, provider_manager, preset_manager
):
    system_message_content = "test system message"
    user_message_content = "test user message"
    assistant_message_content = "test assistant response"
    user_message_content_2 = "test user message 2"
    messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": user_message_content},
        {"role": "assistant", "content": assistant_message_content},
        {"role": "user", "content": user_message_content_2},
    ]
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, input=messages
    )
    result = request.prepare_custom_new_conversation_messages()
    assert len(result) == 4
    assert result[0]["role"] == "system"
    assert result[0]["message"] == system_message_content
    assert result[1]["role"] == "user"
    assert result[1]["message"] == user_message_content
    assert result[2]["role"] == "assistant"
    assert result[2]["message"] == assistant_message_content
    assert result[3]["role"] == "user"
    assert result[3]["message"] == user_message_content_2


def test_prepare_new_conversation_messages_with_message_string_builds_default_messages(
    test_config, tool_manager, provider_manager, preset_manager
):
    input = "test message"
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, input=input
    )
    request.prepare_default_new_conversation_messages = Mock()
    request.prepare_new_conversation_messages()
    request.prepare_default_new_conversation_messages.assert_called_once()


def test_prepare_new_conversation_messages_with_message_list_builds_custom_messages(
    test_config, tool_manager, provider_manager, preset_manager
):
    system_message_content = "test system message"
    user_message_content = "test user message"
    messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": user_message_content},
    ]
    request = make_api_request(
        test_config, tool_manager, provider_manager, preset_manager, input=messages
    )
    request.prepare_custom_new_conversation_messages = Mock()
    request.prepare_new_conversation_messages()
    request.prepare_custom_new_conversation_messages.assert_called_once()


def test_prepare_ask_request(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.prepare_new_conversation_messages = Mock(return_value=["new_message"])
    request.tool_cache = Mock()
    request.tool_cache.add_message_tools = Mock(return_value=["old_message1", "old_message2"])
    request.strip_out_messages_over_max_tokens = Mock(return_value=["old_message2", "new_message"])
    new_messages, messages = request.prepare_ask_request()
    assert new_messages == ["new_message"]
    assert messages == ["old_message2", "new_message"]
    request.strip_out_messages_over_max_tokens.assert_called_once_with(
        ["old_message1", "old_message2", "new_message"], request.max_submission_tokens
    )


def test_strip_out_messages_over_max_tokens_no_messages_stripped(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.token_manager = Mock()
    request.token_manager.get_num_tokens_from_messages = Mock(side_effect=[30, 30])
    messages = ["message1", "message2", "message3"]
    result = request.strip_out_messages_over_max_tokens(messages, 50)
    assert result == messages


def test_strip_out_messages_over_max_tokens_two_messages_stripped(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.token_manager = Mock()
    request.token_manager.get_num_tokens_from_messages = Mock(side_effect=[100, 60, 30, 30])
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    result = request.strip_out_messages_over_max_tokens(messages, 50)
    assert len(result) == 1
    assert result[0] == messages[2]
    captured = capsys.readouterr()
    assert "stripped out 2 oldest messages" in clean_output(captured.out)


def test_strip_out_messages_over_max_tokens_all_messages_stripped(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.token_manager = Mock()
    request.token_manager.get_num_tokens_from_messages = Mock(side_effect=[100, 80, 60, 60])
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    with pytest.raises(Exception) as excinfo:
        request.strip_out_messages_over_max_tokens(messages, 50)
    assert "still over max submission tokens: 50" in str(excinfo.value)


def test_call_llm_streaming(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides={"stream": True},
    )
    built_messages = ["built message"]
    request.build_chat_request = Mock(return_value=built_messages)
    request.execute_llm_streaming = Mock(return_value=(True, "response", "Response received"))
    success, response, user_message = request.call_llm(["message"])
    assert success is True
    assert response == "response"
    assert user_message == "Response received"
    request.execute_llm_streaming.assert_called_once_with(built_messages)


def test_call_llm_non_streaming(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    built_messages = ["built message"]
    request.build_chat_request = Mock(return_value=built_messages)
    request.execute_llm_non_streaming = Mock(return_value=(True, "response", "Response received"))
    success, response, user_message = request.call_llm(["message"])
    assert success is True
    assert response == "response"
    assert user_message == "Response received"
    request.execute_llm_non_streaming.assert_called_once_with(built_messages)


def test_attach_files_no_files(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    messages = ["test message"]
    result = request.attach_files(messages)
    assert result == messages

def test_attach_files_with_files(test_config, tool_manager, provider_manager, preset_manager):
    file = {"type": "image", "url": "test.jpg"}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides={"files": [file]}
    )
    messages = ["test message"]
    result = request.attach_files(messages)
    assert len(result) == 2
    assert result[0] == "test message"
    assert result[1] == file

def test_attach_files_multiple_files(test_config, tool_manager, provider_manager, preset_manager):
    files = [
        {"type": "image", "url": "test1.jpg"},
        {"type": "image", "url": "test2.jpg"}
    ]
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides={"files": files}
    )
    messages = ["test message"]
    result = request.attach_files(messages)
    assert len(result) == 3
    assert result[0] == "test message"
    assert result[1] == files[0]
    assert result[2] == files[1]

def test_build_chat_request(test_config, tool_manager, provider_manager, preset_manager):
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    result = request.build_chat_request(messages)
    assert len(result) == 3
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], HumanMessage)
    assert isinstance(result[2], AIMessage)
    assert result[0].content != ""
    assert result[1].content != ""
    assert result[2].content != ""

def test_build_chat_request_with_files(test_config, tool_manager, provider_manager, preset_manager):
    file = {"type": "image", "url": "test.jpg"}
    request = make_api_request(
        test_config,
        tool_manager,
        provider_manager,
        preset_manager,
        request_overrides={"files": [file]}
    )
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    result = request.build_chat_request(messages)
    assert len(result) == 4  # Original 3 messages + 1 file
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], HumanMessage)
    assert isinstance(result[2], AIMessage)
    assert result[3] == file


def test_output_chunk_content_empty_content(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    callback = Mock()
    request.output_chunk_content("", True, callback)
    captured = capsys.readouterr()
    assert captured.out == ""
    callback.assert_not_called()


def test_output_chunk_content_no_print_no_callback(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    callback = Mock()
    request.output_chunk_content("content", False, None)
    captured = capsys.readouterr()
    assert captured.out == ""
    callback.assert_not_called()


def test_output_chunk_content_print_callback(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    callback = Mock()
    request.output_chunk_content("content", True, callback)
    captured = capsys.readouterr()
    assert captured.out == "content"
    callback.assert_called_once_with("content")


def test_iterate_streaming_response_output_chunk_content_args(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = True
    callback = Mock()
    request.llm = Mock()
    request.llm.stream = Mock(return_value=[AIMessageChunk(content="content1")])
    request.output_chunk_content = Mock()
    request.iterate_streaming_response(TEST_BASIC_MESSAGES, True, callback)
    assert request.output_chunk_content.call_args.args[0] == "content1"
    assert request.output_chunk_content.call_args.args[1] is True
    assert request.output_chunk_content.call_args.args[2] is callback


def test_iterate_streaming_response_messages(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(
        return_value=[
            AIMessageChunk(content="content1"),
            AIMessageChunk(content="content2"),
            AIMessageChunk(content="content3"),
        ]
    )
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert result.content == "content1content2content3"


def test_iterate_streaming_response_strings(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(return_value=["content1", "content2", "content3"])
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert result == "content1content2content3"


def test_iterate_streaming_response_unexpected_chunk_type(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(return_value=[123])
    with pytest.raises(ValueError) as excinfo:
        request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert str(excinfo.value).startswith("Unexpected chunk type")


def test_iterate_streaming_response_tool_call(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(
        return_value=[
            AIMessageChunk(
                content="",
                additional_kwargs={"tool_call": {"name": "test_tool", "arguments": ""}},
            ),
            AIMessageChunk(
                content="", additional_kwargs={"tool_call": {"arguments": '{"arg1": "arg1"}'}}
            ),
        ]
    )
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert result.content == ""
    assert result.additional_kwargs["tool_call"]["name"] == "test_tool"
    assert result.additional_kwargs["tool_call"]["arguments"] == '{"arg1": "arg1"}'


def test_iterate_streaming_response_interrupted_tool_call(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = False
    request.llm = Mock()
    request.llm.stream = Mock(
        return_value=[
            AIMessageChunk(
                content="",
                additional_kwargs={
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                            "function": {"arguments": '{"', "name": "test_tool"},
                            "type": "tool_calls",
                        }
                    ]
                },
                id="run-01744f2e-ccf8-4768-9ba4-64eb6d0644de",
                invalid_tool_calls=[
                    {
                        "name": "test_tool",
                        "args": '{"',
                        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                        "error": None,
                    }
                ],
                tool_call_chunks=[
                    {
                        "name": "test_tool",
                        "args": '{"',
                        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                        "index": 0,
                    }
                ],
            ),
        ]
    )
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    captured = capsys.readouterr()
    assert result is None
    assert "Generation stopped" in captured.out


def test_execute_llm_streaming_no_print_no_callback(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.iterate_streaming_response = Mock(return_value="test response")
    success, response, user_message = request.execute_llm_streaming(TEST_BASIC_MESSAGES)
    assert success is True
    assert response == "test response"
    assert request.iterate_streaming_response.call_args.args[0] == TEST_BASIC_MESSAGES
    assert request.iterate_streaming_response.call_args.args[1] is False
    assert request.iterate_streaming_response.call_args.args[2] is None


def test_execute_llm_streaming_print_callback(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.iterate_streaming_response = Mock(return_value="test response")
    request.request_overrides["print_stream"] = True
    stream_callback = Mock()
    request.request_overrides["stream_callback"] = stream_callback
    success, response, user_message = request.execute_llm_streaming(TEST_BASIC_MESSAGES)
    assert success is True
    assert response == "test response"
    assert request.iterate_streaming_response.call_args.args[0] == TEST_BASIC_MESSAGES
    assert request.iterate_streaming_response.call_args.args[1] is True
    assert request.iterate_streaming_response.call_args.args[2] is stream_callback


def test_execute_llm_streaming_exception(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.iterate_streaming_response = Mock(side_effect=ValueError("Error"))
    success, response, user_message = request.execute_llm_streaming(["message"])
    assert success is False
    assert response == ["message"]
    assert str(user_message) == "Error"
    assert request.streaming is False


def test_execute_llm_non_streaming(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.llm = Mock()
    request.llm.invoke = Mock(return_value="response")
    success, response, user_message = request.execute_llm_non_streaming(TEST_BASIC_MESSAGES)
    assert success is True
    assert response == "response"


def test_execute_llm_non_streaming_failure_call_llm(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.llm = Mock()
    request.llm.invoke = Mock(side_effect=ValueError("Error"))
    success, response_obj, user_message = request.execute_llm_non_streaming(TEST_BASIC_MESSAGES)
    assert success is False
    assert str(user_message) == "Error"


def test_post_response_tool_call(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    response_obj = Mock()
    new_messages = []
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
        },
    ]
    response_message = {
        "message_type": "tool_call",
        "message": tool_calls,
    }
    request.extract_message_content = Mock(return_value=(response_message, tool_calls))
    request.handle_tool_calls = Mock(return_value=("response", new_messages))
    result = request.post_response(response_obj, new_messages)
    assert result == ("response", new_messages)
    request.extract_message_content.assert_called_once_with(response_obj)
    request.handle_tool_calls.assert_called_once_with(tool_calls, new_messages)


def test_post_response_non_tool(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    response_obj = Mock()
    new_messages = []
    tool_calls = []
    response_message = {"message_type": "content", "message": "Hello, world!"}
    request.extract_message_content = Mock(return_value=(response_message, tool_calls))
    request.handle_non_tool_response = Mock(return_value=("response", new_messages))
    result = request.post_response(response_obj, new_messages)
    assert result == ("response", new_messages)
    request.extract_message_content.assert_called_once_with(response_obj)
    request.handle_non_tool_response.assert_called_once_with(response_message, new_messages)


def test_handle_tool_calls_return(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
        },
    ]
    new_messages = []
    request.log_tool_call = Mock()
    request.should_return_on_tool_call = Mock(return_value=True)
    request.execute_tool_calls = Mock()
    result = request.handle_tool_calls(tool_calls, new_messages)
    assert result == (tool_calls, new_messages)
    request.log_tool_call.assert_called_once_with(tool_calls[0])
    request.should_return_on_tool_call.assert_called_once()
    request.execute_tool_calls.assert_not_called()


def test_handle_tool_calls_execute(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
        },
    ]
    response = "response"
    new_messages = []
    request.log_tool_call = Mock()
    request.should_return_on_tool_call = Mock(return_value=False)
    request.execute_tool_calls = Mock(return_value=(response, new_messages))
    result = request.handle_tool_calls(tool_calls, new_messages)
    assert result == (response, new_messages)
    request.log_tool_call.assert_called_once_with(tool_calls[0])
    request.should_return_on_tool_call.assert_called_once()
    request.execute_tool_calls.assert_called_once_with(tool_calls, new_messages)


def test_handle_non_tool_response_return(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    response_message = {"message_type": "content", "message": "Hello, world!"}
    new_messages = []
    request.check_return_on_tool_response = Mock(return_value=("tool_response", new_messages))
    result = request.handle_non_tool_response(response_message, new_messages)
    assert result == ("tool_response", new_messages)
    request.check_return_on_tool_response.assert_called_once_with(new_messages)


def test_handle_non_tool_response_no_return(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    response_message = {"message_type": "content", "message": "Hello, world!"}
    new_messages = []
    request.check_return_on_tool_response = Mock(return_value=(None, new_messages))
    result = request.handle_non_tool_response(response_message, new_messages)
    assert result == (response_message["message"], new_messages)
    request.check_return_on_tool_response.assert_called_once_with(new_messages)


def test_log_tool_call_return_only_false(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_call = {
        "name": "test_tool",
        "args": {
            "word": "foo",
            "repeats": 2,
        },
        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
    }
    util.print_markdown = Mock()
    request.return_only = False
    request.log_tool_call(tool_call)
    util.print_markdown.assert_called_once()


def test_log_tool_call_return_only_true(
    test_config, tool_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_call = {
        "name": "test_tool",
        "args": {
            "word": "foo",
            "repeats": 2,
        },
        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
    }
    util.print_markdown = Mock()
    request.return_only = True
    request.log_tool_call(tool_call)
    util.print_markdown.assert_not_called()


def test_execute_tool_calls_success(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
        }
    ]
    new_messages = []
    tool_response = {
        "result": "foo foo",
    }
    tool_response_message = (
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_tool", "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"},
            "message_type": "tool_response",
            "role": "tool",
        },
    )
    request.execute_tool_call = Mock(return_value=tool_response)
    request.build_tool_response_message = Mock(return_value=tool_response_message)
    request.check_forced_tool = Mock(return_value=False)
    request.call_llm = Mock(return_value=(True, "test response", "LLM call succeeded"))
    request.post_response = Mock(return_value=("test response", new_messages))
    result = request.execute_tool_calls(tool_calls, new_messages)
    assert result == ("test response", new_messages)
    request.execute_tool_call.assert_called_once_with(tool_calls[0])
    request.build_tool_response_message.assert_called_once_with(tool_calls[0], tool_response)
    request.check_forced_tool.assert_called_once()
    request.call_llm.assert_called_once_with(new_messages)
    request.post_response.assert_called_once_with("test response", new_messages)


def test_execute_tool_calls_forced(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
        }
    ]
    new_messages = []
    tool_response = {
        "result": "foo foo",
    }
    tool_response_message = (
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_tool", "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"},
            "message_type": "tool_response",
            "role": "tool",
        },
    )
    request.execute_tool_call = Mock(return_value=tool_response)
    request.build_tool_response_message = Mock(return_value=tool_response_message)
    request.check_forced_tool = Mock(return_value=True)
    request.call_llm = Mock()
    request.post_response = Mock()
    result = request.execute_tool_calls(tool_calls, new_messages)
    assert result == (tool_response, new_messages)
    request.execute_tool_call.assert_called_once_with(tool_calls[0])
    request.build_tool_response_message.assert_called_once_with(tool_calls[0], tool_response)
    request.check_forced_tool.assert_called_once()
    request.call_llm.assert_not_called()
    request.post_response.assert_not_called()


def test_execute_tool_calls_llm_failure(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
        }
    ]
    new_messages = []
    tool_response = {
        "result": "foo foo",
    }
    tool_response_message = (
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_tool", "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"},
            "message_type": "tool_response",
            "role": "tool",
        },
    )
    request.execute_tool_call = Mock(return_value=tool_response)
    request.build_tool_response_message = Mock(return_value=tool_response_message)
    request.check_forced_tool = Mock(return_value=False)
    request.call_llm = Mock(return_value=(False, None, "LLM call failed"))
    request.post_response = Mock()
    with pytest.raises(ValueError) as excinfo:
        request.execute_tool_calls(tool_calls, new_messages)
    assert "LLM call failed" in str(excinfo.value)
    request.execute_tool_call.assert_called_once_with(tool_calls[0])
    request.build_tool_response_message.assert_called_once_with(tool_calls[0], tool_response)
    request.check_forced_tool.assert_called_once()
    request.call_llm.assert_called_once_with(new_messages)
    request.post_response.assert_not_called()


def test_execute_tool_call_success(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_call = {
        "name": "test_tool",
        "args": {
            "word": "foo",
            "repeats": 2,
        },
        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
    }
    tool_response = {
        "result": "foo foo",
    }
    request.run_tool = Mock(return_value=(True, tool_response, "Tool executed successfully"))
    result = request.execute_tool_call(tool_call)
    assert result == tool_response
    request.run_tool.assert_called_once_with(tool_call["name"], tool_call["args"])


def test_execute_tool_call_failure(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_call = {
        "name": "test_tool",
        "args": {
            "word": "foo",
            "repeats": 2,
        },
        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
    }
    request.run_tool = Mock(return_value=(False, None, "Tool call failed"))
    with pytest.raises(ValueError) as excinfo:
        request.execute_tool_call(tool_call)
    assert "Tool call failed" in str(excinfo.value)
    request.run_tool.assert_called_once_with(tool_call["name"], tool_call["args"])


def test_build_tool_response_message_no_id(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_call = {"name": "test_tool", "args": {"word": "foo", "repeats": 2}}
    tool_response = {"message": "Repeated the word foo 2 times.", "result": "foo foo"}
    result = request.build_tool_response_message(tool_call, tool_response)
    assert result == {
        "role": "tool",
        "message": tool_response,
        "message_type": "tool_response",
        "message_metadata": {"name": tool_call["name"]},
    }


def test_build_tool_response_message_with_id(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_call = {
        "name": "test_tool",
        "args": {"word": "foo", "repeats": 2},
        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
    }
    tool_response = {"message": "Repeated the word foo 2 times.", "result": "foo foo"}
    result = request.build_tool_response_message(tool_call, tool_response)
    assert result == {
        "role": "tool",
        "message": tool_response,
        "message_type": "tool_response",
        "message_metadata": {"name": tool_call["name"], "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI"},
    }


@patch("lwe.backends.api.request.convert_message_to_dict")
def test_extract_message_content_no_tool_calls(
    mock_convert_message_to_dict, test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    content = "test"
    message_dict = {
        "role": "assistant",
        "content": content,
    }
    ai_message = AIMessage(
        content=content,
        additional_kwargs={},
        tool_calls=[],
    )
    mock_convert_message_to_dict.return_value = message_dict
    request.message = Mock()
    request.message.build_message = Mock(return_value=message_dict)
    message_result, tool_calls_result = request.extract_message_content(ai_message)
    assert message_result == message_dict
    assert tool_calls_result == []
    mock_convert_message_to_dict.assert_called_once_with(ai_message)
    request.message.build_message.assert_called_once_with(
        message_dict["role"], message_dict["content"], "content"
    )


@patch("lwe.backends.api.request.convert_message_to_dict")
def test_extract_message_content_tool_call(
    mock_convert_message_to_dict, test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "name": "test_tool",
            "args": {
                "word": "foo",
                "repeats": 2,
            },
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
            "type": "tool_call",
        },
    ]
    message_dict = {
        "role": "assistant",
        "content": "",
    }
    message = {
        "role": "assistant",
        "message": tool_calls,
        "message_type": "tool_call",
    }
    ai_message = AIMessage(
        content="",
        additional_kwargs={
            "tool_calls": [
                {
                    "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                    "type": "tool_call",
                    "function": {
                        "name": "test_tool",
                        "arguments": '{"word": "foo", "repeats": 2}',
                    },
                },
            ]
        },
        tool_calls=tool_calls,
    )
    mock_convert_message_to_dict.return_value = message_dict
    request.message = Mock()
    request.message.build_message = Mock(return_value=message)
    message_result, tool_calls_result = request.extract_message_content(ai_message)
    assert message_result == message
    assert tool_calls_result == tool_calls
    mock_convert_message_to_dict.assert_called_once_with(ai_message)
    request.message.build_message.assert_called_once_with(
        message_dict["role"], tool_calls, "tool_call"
    )


@patch("lwe.backends.api.request.convert_message_to_dict")
def test_extract_message_content_invalid_tool_calls(
    mock_convert_message_to_dict, test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = [
        {
            "index": 0,
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
            "function": {"arguments": '{"', "name": "test_tool"},
            "type": "tool_calls",
        }
    ]
    invalid_tool_calls = [
        {
            "name": "test_tool",
            "args": "",
            "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
            "error": "Some error occurred",
        }
    ]
    ai_message = AIMessage(
        content="",
        additional_kwargs={
            "tool_calls": tool_calls,
        },
        id="run-01744f2e-ccf8-4768-9ba4-64eb6d0644de",
        invalid_tool_calls=invalid_tool_calls,
    )
    with pytest.raises(RuntimeError) as excinfo:
        request.extract_message_content(ai_message)
    assert "LLM tool call failed:" in str(excinfo.value)


@patch("lwe.backends.api.request.convert_message_to_dict")
def test_extract_message_content_string(
    mock_convert_message_to_dict, test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    tool_calls = []
    string_message = "test_message"
    message = {
        "role": "assistant",
        "message": string_message,
        "message_type": "content",
    }
    request.message = Mock()
    request.message.build_message = Mock(return_value=message)
    message_result, tool_calls_result = request.extract_message_content(string_message)
    assert message_result == message
    assert tool_calls_result == tool_calls
    mock_convert_message_to_dict.assert_not_called()
    request.message.build_message.assert_called_once_with("assistant", string_message)


def test_should_return_on_tool_call(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({"return_on_tool_call": True}, {})
    assert request.should_return_on_tool_call() is True


def test_check_forced_tool_no_tool_choice(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({}, {})
    assert request.check_forced_tool() is False


def test_check_forced_tool_auto(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({}, {"tool_choice": "auto"})
    assert request.check_forced_tool() is False


def test_check_forced_tool_none(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({}, {"tool_choice": "none"})
    assert request.check_forced_tool() is False


def test_check_forced_tool_other_string(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({}, {"tool_choice": "any"})
    assert request.check_forced_tool() is True


def test_check_forced_tool_non_string(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({}, {"tool_choice": {"name": "test_tool"}})
    assert request.check_forced_tool() is True


def test_check_return_on_tool_response_not_set(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({}, {})
    tool_response, new_messages = request.check_return_on_tool_response(
        copy.deepcopy(TEST_TOOL_CALL_RESPONSE_MESSAGES)
    )
    assert tool_response is None
    assert new_messages == TEST_TOOL_CALL_RESPONSE_MESSAGES


def test_check_return_on_tool_response_true(
    test_config, tool_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.preset = ({"return_on_tool_response": True}, {})
    tool_response, new_messages = request.check_return_on_tool_response(
        copy.deepcopy(TEST_TOOL_CALL_RESPONSE_MESSAGES)
    )
    assert tool_response == {"message": "Repeated the word foo 2 times.", "result": "foo foo"}
    assert len(new_messages) == len(TEST_TOOL_CALL_RESPONSE_MESSAGES) - 1


def test_run_tool_success(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    run_tool_result = {"result": "test"}
    request.tool_manager.run_tool = Mock(return_value=(True, run_tool_result, "message"))
    success, json_obj, user_message = request.run_tool("test_tool", {})
    assert success is True
    assert json_obj == run_tool_result


def test_run_tool_failure(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.tool_manager.run_tool = Mock(return_value=(False, None, "message"))
    success, json_obj, user_message = request.run_tool("test_tool", {})
    assert success is False
    assert json_obj == {"error": "message"}


def test_is_tool_response_message(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    assert request.is_tool_response_message({"message_type": "tool_response"}) is True


def test_terminate_stream(test_config, tool_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, tool_manager, provider_manager, preset_manager)
    request.streaming = True
    request.terminate_stream(None, None)
    assert request.streaming is False
