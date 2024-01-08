import copy
import pytest

from unittest.mock import Mock

from langchain.schema.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    FunctionMessage,
    AIMessageChunk,
)

from lwe.core import constants
from lwe.core.token_manager import TokenManager
from ..base import (
    clean_output,
    make_provider,
    make_api_request,
    TEST_BASIC_MESSAGES,
    TEST_FUNCTION_CALL_RESPONSE_MESSAGES,
)


def test_init_with_defaults(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider
    )
    assert request.config == test_config
    assert request.provider == provider
    assert request.provider_manager == provider_manager
    assert request.function_manager == function_manager
    assert request.input == "test"
    assert request.default_preset is None
    assert request.default_preset_name is None
    assert request.preset_manager == preset_manager


def test_init_with_request_overrides(
    test_config, function_manager, provider_manager, preset_manager
):
    request_overrides = {"stream": True}
    request = make_api_request(
        test_config,
        function_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    assert request.request_overrides == request_overrides


def test_init_with_preset(test_config, function_manager, provider_manager, preset_manager):
    preset = preset_manager.presets["test"]
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, preset=preset
    )
    assert request.default_preset == preset
    assert request.default_preset_name == "test"


def test_set_request_llm_success(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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


def test_set_request_llm_failure(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.extract_metadata_customizations = Mock(return_value=(False, None, "Error"))
    success, response, user_message = request.set_request_llm()
    assert success is False
    assert response is None
    assert user_message == "Error"


def test_setup_request_config_success(
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider
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


def test_setup_request_config_failure(
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider
    )
    request.build_request_config = Mock(return_value=(False, None, "Error"))
    success, response, user_message = request.setup_request_config(
        "preset_name", {"key": "value"}, {"key": "value"}, {"key": "value"}
    )
    assert success is False
    assert response is None


def test_build_request_config_success_no_preset_name(
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    provider.make_llm = Mock(return_value=Mock(model_name=constants.API_BACKEND_DEFAULT_MODEL))
    request.load_provider = Mock(return_value=(True, provider, "Success"))
    request.merge_preset_overrides = Mock(
        return_value={
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    request.expand_functions = Mock(return_value={"key": "value"})
    request.function_cache = Mock()
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
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider
    )
    provider.make_llm = Mock(return_value=Mock(model_name=constants.API_BACKEND_DEFAULT_MODEL))
    request.merge_preset_overrides = Mock(
        return_value={
            "metadata": {"one": "two"},
            "customizations": {"three": "four"},
            "preset_overrides": {"five": "six"},
        }
    )
    request.expand_functions = Mock(return_value={"key": "value"})
    request.function_cache = Mock()
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


def test_build_request_config_failure(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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


def test_prepare_config(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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


def test_prepare_config_defaults(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    config = request.prepare_config(
        {"preset_name": None, "metadata": None, "customizations": None, "preset_overrides": None}
    )
    assert config == {
        "preset_name": None,
        "metadata": {},
        "customizations": {},
        "preset_overrides": {},
    }


def test_load_provider_with_preset_name(
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider
    )
    request.provider_manager.load_provider = Mock()
    config = {"preset_name": "test", "metadata": {"provider": "test_provider"}}
    success, response, user_message = request.load_provider(config)
    assert success is True
    assert response == provider
    request.provider_manager.load_provider.assert_not_called()


def test_load_provider_without_preset_name(
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.provider_manager.load_provider = Mock(return_value=(True, provider, "Success"))
    config = {"preset_name": None, "metadata": {"provider": "test_provider"}}
    success, response, user_message = request.load_provider(config)
    assert success is True
    assert response == provider
    request.provider_manager.load_provider.assert_called_once_with("test_provider")


def test_merge_preset_overrides(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider
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
    test_config, function_manager, provider_manager, preset_manager
):
    request_overrides = {"preset": "test_preset"}
    request = make_api_request(
        test_config,
        function_manager,
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
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(
        test_config,
        function_manager,
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
        {"key": "value"},
    )


def test_extract_metadata_customizations_with_preset_overrides(
    test_config, function_manager, provider_manager, preset_manager
):
    request_overrides = {"preset": "test_preset", "preset_overrides": {"key": "value"}}
    request = make_api_request(
        test_config,
        function_manager,
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
    test_config, function_manager, provider_manager, preset_manager
):
    provider = make_provider(provider_manager)
    provider.get_customizations = Mock(return_value={"key": "value"})
    request = make_api_request(
        test_config, function_manager, provider_manager, preset_manager, provider=provider
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert success
    assert response == (None, None, {"provider": provider.name}, {"key": "value"})


def test_extract_metadata_customizations_with_invalid_request_overrides(
    test_config, function_manager, provider_manager, preset_manager
):
    request_overrides = {"preset_overrides": {"key": "value"}}
    request = make_api_request(
        test_config,
        function_manager,
        provider_manager,
        preset_manager,
        request_overrides=request_overrides,
    )
    success, response, user_message = request.extract_metadata_customizations()
    assert not success
    assert response == (None, None, False)


def test_extract_metadata_customizations_with_failed_preset_ensuring(
    test_config, function_manager, provider_manager, preset_manager
):
    request_overrides = {"preset": "test_preset"}
    request = make_api_request(
        test_config,
        function_manager,
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
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    preset_manager.ensure_preset = Mock(return_value=(False, "error", "user_message"))
    success, response, user_message = request.get_preset_metadata_customizations("test_preset")
    assert not success
    assert response == "error"
    assert user_message == "user_message"


def test_expand_functions_none(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    customizations = {}
    result = request.expand_functions(customizations)
    assert result == {}


def test_expand_functions_valid_functions(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_manager.get_function_config = Mock(
        side_effect=["function_config1", "function_config2"]
    )
    customizations = {"model_kwargs": {"functions": ["test_function", "test_function2"]}}
    result = request.expand_functions(customizations)
    assert result["model_kwargs"]["functions"] == ["function_config1", "function_config2"]


def test_expand_functions_missing_function(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    customizations = {"model_kwargs": {"functions": ["test_missing_function"]}}
    with pytest.raises(ValueError) as excinfo:
        request.expand_functions(customizations)
    assert "test_missing_function not found" in str(excinfo.value)


def test_prepare_new_conversation_messages_no_old_messages_system_message_default(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.old_messages = []
    request.input = "test message"
    result = request.prepare_new_conversation_messages()
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["message"] == constants.SYSTEM_MESSAGE_DEFAULT
    assert result[1]["role"] == "user"
    assert result[1]["message"] == "test message"


def test_prepare_new_conversation_messages_no_old_messages_system_message_override(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.old_messages = []
    request.input = "test message"
    request.request_overrides["system_message"] = "test system message"
    result = request.prepare_new_conversation_messages()
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["message"] == "test system message"
    assert result[1]["role"] == "user"
    assert result[1]["message"] == "test message"


def test_prepare_new_conversation_messages_old_messages(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.old_messages = TEST_BASIC_MESSAGES
    request.input = "test message"
    result = request.prepare_new_conversation_messages()
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["message"] == "test message"


def test_prepare_ask_request(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.prepare_new_conversation_messages = Mock(return_value=["new_message"])
    request.function_cache = Mock()
    request.function_cache.add_message_functions = Mock(
        return_value=["old_message1", "old_message2"]
    )
    request.strip_out_messages_over_max_tokens = Mock(return_value=["old_message2", "new_message"])
    new_messages, messages = request.prepare_ask_request()
    assert new_messages == ["new_message"]
    assert messages == ["old_message2", "new_message"]
    request.strip_out_messages_over_max_tokens.assert_called_once_with(
        ["old_message1", "old_message2", "new_message"], request.max_submission_tokens
    )


def test_strip_out_messages_over_max_tokens_no_messages_stripped(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.token_manager = Mock()
    request.token_manager.get_num_tokens_from_messages = Mock(side_effect=[30, 30])
    messages = ["message1", "message2", "message3"]
    result = request.strip_out_messages_over_max_tokens(messages, 50)
    assert result == messages


def test_strip_out_messages_over_max_tokens_two_messages_stripped(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.token_manager = Mock()
    request.token_manager.get_num_tokens_from_messages = Mock(side_effect=[100, 60, 30, 30])
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    result = request.strip_out_messages_over_max_tokens(messages, 50)
    assert len(result) == 1
    assert result[0] == messages[2]
    captured = capsys.readouterr()
    assert "stripped out 2 oldest messages" in clean_output(captured.out)


def test_strip_out_messages_over_max_tokens_all_messages_stripped(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.token_manager = Mock()
    request.token_manager.get_num_tokens_from_messages = Mock(side_effect=[100, 80, 60, 60])
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    with pytest.raises(Exception) as excinfo:
        request.strip_out_messages_over_max_tokens(messages, 50)
    assert "still over max submission tokens: 50" in str(excinfo.value)


def test_call_llm_streaming(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(
        test_config,
        function_manager,
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


def test_call_llm_non_streaming(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    built_messages = ["built message"]
    request.build_chat_request = Mock(return_value=built_messages)
    request.execute_llm_non_streaming = Mock(return_value=(True, "response", "Response received"))
    success, response, user_message = request.call_llm(["message"])
    assert success is True
    assert response == "response"
    assert user_message == "Response received"
    request.execute_llm_non_streaming.assert_called_once_with(built_messages)


def test_build_chat_request(test_config, function_manager, provider_manager, preset_manager):
    messages = copy.deepcopy(TEST_BASIC_MESSAGES)
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    result = request.build_chat_request(messages)
    assert len(result) == 3
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], HumanMessage)
    assert isinstance(result[2], AIMessage)
    assert result[0].content != ""
    assert result[1].content != ""
    assert result[2].content != ""


def test_output_chunk_content_empty_content(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    callback = Mock()
    request.output_chunk_content("", True, callback)
    captured = capsys.readouterr()
    assert captured.out == ""
    callback.assert_not_called()


def test_output_chunk_content_no_print_no_callback(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    callback = Mock()
    request.output_chunk_content("content", False, None)
    captured = capsys.readouterr()
    assert captured.out == ""
    callback.assert_not_called()


def test_output_chunk_content_print_callback(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    callback = Mock()
    request.output_chunk_content("content", True, callback)
    captured = capsys.readouterr()
    assert captured.out == "content"
    callback.assert_called_once_with("content")


def test_iterate_streaming_response_output_chunk_content_args(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(return_value=["content1", "content2", "content3"])
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert result == "content1content2content3"


def test_iterate_streaming_response_unexpected_chunk_type(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(return_value=[123])
    with pytest.raises(ValueError) as excinfo:
        request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert str(excinfo.value).startswith("Unexpected chunk type")


def test_iterate_streaming_response_function_call(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.streaming = True
    request.llm = Mock()
    request.llm.stream = Mock(
        return_value=[
            AIMessageChunk(
                content="",
                additional_kwargs={"function_call": {"name": "test_function", "arguments": ""}},
            ),
            AIMessageChunk(
                content="", additional_kwargs={"function_call": {"arguments": '{"arg1": "arg1"}'}}
            ),
        ]
    )
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    assert result.content == ""
    assert result.additional_kwargs["function_call"]["name"] == "test_function"
    assert result.additional_kwargs["function_call"]["arguments"] == '{"arg1": "arg1"}'


def test_iterate_streaming_response_interrupted_function_call(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.streaming = False
    request.llm = Mock()
    request.llm.stream = Mock(
        return_value=[
            AIMessageChunk(
                content="",
                additional_kwargs={"function_call": {"name": "test_function", "arguments": ""}},
            ),
        ]
    )
    result = request.iterate_streaming_response(TEST_BASIC_MESSAGES, False, None)
    captured = capsys.readouterr()
    assert result is None
    assert "Generation stopped" in captured.out


def test_execute_llm_streaming_no_print_no_callback(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.iterate_streaming_response = Mock(return_value="test response")
    success, response, user_message = request.execute_llm_streaming(TEST_BASIC_MESSAGES)
    assert success is True
    assert response == "test response"
    assert request.iterate_streaming_response.call_args.args[0] == TEST_BASIC_MESSAGES
    assert request.iterate_streaming_response.call_args.args[1] is False
    assert request.iterate_streaming_response.call_args.args[2] is None


def test_execute_llm_streaming_print_callback(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
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
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.iterate_streaming_response = Mock(side_effect=ValueError("Error"))
    success, response, user_message = request.execute_llm_streaming(["message"])
    assert success is False
    assert response == ["message"]
    assert str(user_message) == "Error"
    assert request.streaming is False


def test_execute_llm_non_streaming(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.llm = Mock()
    request.llm.invoke = Mock(return_value="response")
    success, response, user_message = request.execute_llm_non_streaming(TEST_BASIC_MESSAGES)
    assert success is True
    assert response == "response"


def test_execute_llm_non_streaming_failure_call_llm(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.llm = Mock()
    request.llm.invoke = Mock(side_effect=ValueError("Error"))
    success, response_obj, user_message = request.execute_llm_non_streaming(TEST_BASIC_MESSAGES)
    assert success is False
    assert str(user_message) == "Error"


def test_post_response_function_call(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    response_obj = Mock()
    new_messages = []
    response_message = {
        "message_type": "function_call",
        "message": {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}},
    }
    request.extract_message_content = Mock(return_value=response_message)
    request.handle_function_call = Mock(return_value=("response", new_messages))
    result = request.post_response(response_obj, new_messages)
    assert result == ("response", new_messages)
    request.extract_message_content.assert_called_once_with(response_obj)
    request.handle_function_call.assert_called_once_with(response_message, new_messages)


def test_post_response_non_function(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    response_obj = Mock()
    new_messages = []
    response_message = {"message_type": "content", "message": "Hello, world!"}
    request.extract_message_content = Mock(return_value=response_message)
    request.handle_non_function_response = Mock(return_value=("response", new_messages))
    result = request.post_response(response_obj, new_messages)
    assert result == ("response", new_messages)
    request.extract_message_content.assert_called_once_with(response_obj)
    request.handle_non_function_response.assert_called_once_with(response_message, new_messages)


def test_handle_function_call_return(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    response_message = {
        "message_type": "function_call",
        "message": {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}},
    }
    new_messages = []
    request.log_function_call = Mock()
    request.should_return_on_function_call = Mock(return_value=True)
    request.build_function_definition = Mock(return_value="function_definition")
    result = request.handle_function_call(response_message, new_messages)
    assert result == ("function_definition", new_messages)
    request.log_function_call.assert_called_once_with(response_message["message"])
    request.should_return_on_function_call.assert_called_once()
    request.build_function_definition.assert_called_once_with(response_message["message"])


def test_handle_function_call_execute(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    response_message = {
        "message_type": "function_call",
        "message": {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}},
    }
    new_messages = []
    request.log_function_call = Mock()
    request.should_return_on_function_call = Mock(return_value=False)
    request.execute_function_call = Mock(return_value=("function_response", new_messages))
    result = request.handle_function_call(response_message, new_messages)
    assert result == ("function_response", new_messages)
    request.log_function_call.assert_called_once_with(response_message["message"])
    request.should_return_on_function_call.assert_called_once()
    request.execute_function_call.assert_called_once_with(response_message["message"], new_messages)


def test_handle_non_function_response_return(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    response_message = {"message_type": "content", "message": "Hello, world!"}
    new_messages = []
    request.check_return_on_function_response = Mock(
        return_value=("function_response", new_messages)
    )
    result = request.handle_non_function_response(response_message, new_messages)
    assert result == ("function_response", new_messages)
    request.check_return_on_function_response.assert_called_once_with(new_messages)


def test_handle_non_function_response_no_return(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    response_message = {"message_type": "content", "message": "Hello, world!"}
    new_messages = []
    request.check_return_on_function_response = Mock(return_value=(None, new_messages))
    result = request.handle_non_function_response(response_message, new_messages)
    assert result == (response_message["message"], new_messages)
    request.check_return_on_function_response.assert_called_once_with(new_messages)


def test_log_function_call_return_only_false(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    request.return_only = False
    request.log_function_call(function_call)
    captured = capsys.readouterr()
    assert "AI requested function call" in captured.out


def test_log_function_call_return_only_true(
    test_config, function_manager, provider_manager, preset_manager, capsys
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    request.return_only = True
    request.log_function_call(function_call)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_build_function_definition(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    result = request.build_function_definition(function_call)
    assert result["name"] == function_call["name"]
    assert result["arguments"] == function_call["arguments"]


def test_execute_function_call_success(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    new_messages = []
    function_response = {
        "result": "foo foo",
    }
    request.run_function = Mock(return_value=(True, function_response, "Function call succeeded"))
    function_response_message = (
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_function"},
            "message_type": "function_response",
            "role": "function",
        },
    )
    request.build_function_response_message = Mock(return_value=function_response_message)
    request.check_forced_function = Mock(return_value=False)
    request.call_llm = Mock(return_value=(True, "test response", "LLM call succeeded"))
    request.post_response = Mock(return_value=("test response", new_messages))
    result = request.execute_function_call(function_call, new_messages)
    assert result == ("test response", new_messages)
    request.run_function.assert_called_once_with(function_call["name"], function_call["arguments"])
    request.build_function_response_message.assert_called_once_with(
        function_call, function_response
    )
    request.check_forced_function.assert_called_once()
    request.call_llm.assert_called_once_with(new_messages)
    request.post_response.assert_called_once_with("test response", new_messages)


def test_execute_function_call_forced(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}

    function_response = {
        "result": "foo foo",
    }
    function_response_message = (
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_function"},
            "message_type": "function_response",
            "role": "function",
        },
    )
    new_messages = []
    request.run_function = Mock(return_value=(True, function_response, "Function call succeeded"))
    request.build_function_response_message = Mock(return_value=function_response_message)
    request.check_forced_function = Mock(return_value=True)
    result = request.execute_function_call(function_call, new_messages)
    assert result == (function_response, new_messages)
    request.run_function.assert_called_once_with(function_call["name"], function_call["arguments"])
    request.build_function_response_message.assert_called_once_with(
        function_call, function_response
    )
    request.check_forced_function.assert_called_once()


def test_execute_function_call_llm_failure(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    function_response = {
        "result": "foo foo",
    }
    function_response_message = (
        {
            "message": {"message": "Repeated the word foo 2 times.", "result": "foo foo"},
            "message_metadata": {"name": "test_function"},
            "message_type": "function_response",
            "role": "function",
        },
    )
    new_messages = []
    request.run_function = Mock(return_value=(True, function_response, "Function call succeeded"))
    request.build_function_response_message = Mock(return_value=function_response_message)
    request.check_forced_function = Mock(return_value=False)
    request.call_llm = Mock(return_value=(False, None, "LLM call failed"))
    with pytest.raises(ValueError) as excinfo:
        request.execute_function_call(function_call, new_messages)
    assert "LLM call failed" in str(excinfo.value)
    request.run_function.assert_called_once_with(function_call["name"], function_call["arguments"])
    request.build_function_response_message.assert_called_once_with(
        function_call, function_response
    )
    request.check_forced_function.assert_called_once()
    request.call_llm.assert_called_once_with(new_messages)


def test_execute_function_call_failure(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    new_messages = []
    request.run_function = Mock(return_value=(False, None, "Function call failed"))
    with pytest.raises(ValueError) as excinfo:
        request.execute_function_call(function_call, new_messages)
    assert "Function call failed" in str(excinfo.value)
    request.run_function.assert_called_once_with(function_call["name"], function_call["arguments"])


def test_build_function_response_message(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_call = {"name": "test_function", "arguments": {"word": "foo", "repeats": 2}}
    function_response = {"message": "Repeated the word foo 2 times.", "result": "foo foo"}
    result = request.build_function_response_message(function_call, function_response)
    assert result == {
        "role": "function",
        "message": function_response,
        "message_type": "function_response",
        "message_metadata": {"name": function_call["name"]},
    }


def test_extract_message_content_function_call(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    ai_message = AIMessage(
        content="",
        additional_kwargs={
            "function_call": {"name": "test_function", "arguments": '{\n  "one": "test"\n}'}
        },
    )
    message = request.extract_message_content(ai_message)
    assert message["role"] == "assistant"
    assert message["message"]["name"] == "test_function"
    assert message["message_type"] == "function_call"


def test_extract_message_content_function_response(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_response = '{"result": "test"}'
    ai_message = FunctionMessage(content=function_response, name="test_function")
    message = request.extract_message_content(ai_message)
    assert message["role"] == "function"
    assert message["message"] == function_response
    assert message["message_type"] == "function_response"


def test_extract_message_content_string(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    string_message = "test_message"
    message = request.extract_message_content(string_message)
    assert message["role"] == "assistant"
    assert message["message"] == string_message
    assert message["message_type"] == "content"


def test_should_return_on_function_call(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({"return_on_function_call": True}, {})
    assert request.should_return_on_function_call() is True


def test_check_forced_function(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({}, {"model_kwargs": {"function_call": {}}})
    assert request.check_forced_function() is True


def test_check_return_on_function_response_not_set(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({}, {})
    function_response, new_messages = request.check_return_on_function_response(
        copy.deepcopy(TEST_FUNCTION_CALL_RESPONSE_MESSAGES)
    )
    assert function_response is None
    assert len(new_messages) == len(TEST_FUNCTION_CALL_RESPONSE_MESSAGES)


def test_check_return_on_function_response_true(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({"return_on_function_response": True}, {})
    function_response, new_messages = request.check_return_on_function_response(
        copy.deepcopy(TEST_FUNCTION_CALL_RESPONSE_MESSAGES)
    )
    assert function_response == {"message": "Repeated the word foo 2 times.", "result": "foo foo"}
    assert len(new_messages) == len(TEST_FUNCTION_CALL_RESPONSE_MESSAGES) - 1


def test_run_function_success(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    run_function_result = {"result": "test"}
    request.function_manager.run_function = Mock(
        return_value=(True, run_function_result, "message")
    )
    success, json_obj, user_message = request.run_function("test_function", {})
    assert success is True
    assert json_obj == run_function_result


def test_run_function_failure(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.function_manager.run_function = Mock(return_value=(False, None, "message"))
    success, json_obj, user_message = request.run_function("test_function", {})
    assert success is False
    assert json_obj == {"error": "message"}


def test_is_function_response_message(
    test_config, function_manager, provider_manager, preset_manager
):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    assert request.is_function_response_message({"message_type": "function_response"}) is True


def test_terminate_stream(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.streaming = True
    request.terminate_stream(None, None)
    assert request.streaming is False
