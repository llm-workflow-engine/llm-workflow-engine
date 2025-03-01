#!/usr/bin/env python

from unittest.mock import patch
import logging

from langchain_core.messages import AIMessage

from ..base import (
    fake_llm_responses,
)

from lwe import ApiBackend
from lwe.core import constants

from lwe.core import util

DEBUG = False


def make_api_backend(test_config, datadir, user_id=1):
    if user_id is not None:
        test_config.set("backend_options.default_user", user_id)
    if DEBUG:
        test_config.set("log.console.level", "debug")
        test_config.set("debug.log.enabled", True)
    template_dir = str(datadir.absolute())
    test_config.set("directories.templates", [template_dir])
    backend = ApiBackend(test_config)
    if DEBUG:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
    return backend


def get_template_user_message(backend):
    success, response, _user_message = backend.get_conversation()
    assert success
    message_user = response["messages"][1]
    return message_user


def test_api_backend_template_simple(test_config, datadir):
    backend = make_api_backend(test_config, datadir)
    success, response, user_message = backend.run_template("test_template_simple.md")
    assert success
    message_user = get_template_user_message(backend)
    assert "template content" in message_user["message"]


def test_api_backend_template_variable_substitution(test_config, datadir):
    backend = make_api_backend(test_config, datadir)
    template_variables = {
        "passed_variable": "passed_variable_value",
    }
    with patch("pyperclip.paste", return_value="clipboard_value"):
        success, response, user_message = backend.run_template(
            "test_template_variable_substitution.md", template_variables
        )
    assert success
    message_user = get_template_user_message(backend)
    message = message_user["message"]
    assert "passed_variable_value" in message
    assert "frontmatter_variable_value" in message
    assert "clipboard_value" in message
    assert "template content" in message


def test_api_backend_template_non_streaming_valid_response_no_user(test_config, datadir):
    backend = make_api_backend(test_config, datadir, user_id=None)
    success, response, _user_message = backend.run_template("test_template_simple.md")
    assert success
    assert response == "test response"
    assert backend.conversation_id is None


def test_api_backend_template_non_streaming_valid_response_with_user(test_config, datadir):
    backend = make_api_backend(test_config, datadir)
    success, response, _user_message = backend.run_template("test_template_simple.md")
    assert success
    assert response == "test response"
    assert backend.conversation_id == 1


def test_api_backend_template_creates_valid_conversation_and_messages(test_config, datadir):
    backend = make_api_backend(test_config, datadir)
    success, response, _user_message = backend.run_template("test_template_simple.md")
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert response["conversation"]["id"] == 1
    assert response["conversation"]["title"] == "test response"
    assert len(response["messages"]) == 3
    message_system = response["messages"][0]
    message_user = response["messages"][1]
    message_assistant = response["messages"][2]
    assert message_system["role"] == "system"
    assert message_system["message"] == constants.SYSTEM_MESSAGE_DEFAULT
    assert message_system["message_type"] == "content"
    assert message_system["provider"] == "provider_fake_llm"
    assert message_system["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_system["preset"] == "test"
    assert message_user["role"] == "user"
    assert "template content" in message_user["message"]
    assert message_user["message_type"] == "content"
    assert message_user["provider"] == "provider_fake_llm"
    assert message_user["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_user["preset"] == "test"
    assert message_assistant["role"] == "assistant"
    assert message_assistant["message"] == "test response"
    assert message_assistant["message_type"] == "content"
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_assistant["preset"] == "test"


def test_api_backend_template_with_tool_call_creates_valid_conversation_and_messages(
    test_config, datadir
):
    backend = make_api_backend(test_config, datadir)
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
    tool_response_metadata = {
        "name": tool_calls[0]["name"],
        "id": tool_calls[0]["id"],
    }
    tool_response_data = {
        "message": "Repeated the word foo 2 times.",
        "result": "foo foo",
    }
    tool_responses = [
        AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                        "type": "tool_calls",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{"word": "foo", "repeats": 2}',
                        },
                    },
                ]
            },
            tool_calls=tool_calls,
        ),
        "Foo repeated twice is: foo foo",
    ]
    overrides = {"request_overrides": fake_llm_responses(tool_responses)}
    success, response, _user_message = backend.run_template(
        "test_template_tool_call_basic.md", None, overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert len(response["messages"]) == 5
    message_system = response["messages"][0]
    message_user = response["messages"][1]
    message_tool_call = response["messages"][2]
    message_tool_response = response["messages"][3]
    message_assistant = response["messages"][4]
    assert message_system["role"] == "system"
    assert message_system["message"] == constants.SYSTEM_MESSAGE_DEFAULT
    assert message_system["message_type"] == "content"
    assert message_system["provider"] == "provider_fake_llm"
    assert message_system["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_system["preset"] == "test"
    assert message_user["role"] == "user"
    assert "template content" in message_user["message"]
    assert message_user["message_type"] == "content"
    assert message_user["provider"] == "provider_fake_llm"
    assert message_user["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_user["preset"] == "test"
    assert message_tool_call["role"] == "assistant"
    assert message_tool_call["message_type"] == "tool_call"
    assert message_tool_call["message_metadata"] is None
    assert message_tool_call["message"] == tool_calls
    assert message_tool_call["provider"] == "provider_fake_llm"
    assert message_tool_call["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_tool_call["preset"] == "test"
    assert message_tool_response["role"] == "tool"
    assert message_tool_response["message_type"] == "tool_response"
    assert message_tool_response["message_metadata"] == tool_response_metadata
    assert message_tool_response["message"] == tool_response_data
    assert message_tool_response["message_type"] == "tool_response"
    assert message_tool_response["provider"] == "provider_fake_llm"
    assert message_tool_response["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_tool_response["preset"] == "test"
    assert message_assistant["role"] == "assistant"
    assert message_assistant["message"] == "Foo repeated twice is: foo foo"
    assert message_assistant["message_type"] == "content"
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_assistant["preset"] == "test"


def test_api_backend_template_with_tool_call_and_return_on_tool_call_creates_valid_conversation_and_messages(
    test_config,
    datadir,
):
    backend = make_api_backend(test_config, datadir)
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
    tool_responses = [
        AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                        "type": "tool_calls",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{"word": "foo", "repeats": 2}',
                        },
                    },
                ]
            },
            tool_calls=tool_calls,
        ),
        "Foo repeated twice is: foo foo",
    ]
    overrides = {"request_overrides": fake_llm_responses(tool_responses)}
    success, response, _user_message = backend.run_template(
        "test_template_with_tool_call_and_return_on_tool_call.md", None, overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert len(response["messages"]) == 3
    message_system = response["messages"][0]
    message_user = response["messages"][1]
    message_tool_call = response["messages"][2]
    assert message_system["role"] == "system"
    assert message_system["message"] == constants.SYSTEM_MESSAGE_DEFAULT
    assert message_system["message_type"] == "content"
    assert message_system["provider"] == "provider_fake_llm"
    assert message_system["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_system["preset"] == "test"
    assert message_user["role"] == "user"
    assert "template content" in message_user["message"]
    assert message_user["message_type"] == "content"
    assert message_user["provider"] == "provider_fake_llm"
    assert message_user["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_user["preset"] == "test"
    assert message_tool_call["role"] == "assistant"
    assert message_tool_call["message_type"] == "tool_call"
    assert message_tool_call["message_metadata"] is None
    assert message_tool_call["message"] == tool_calls
    assert message_tool_call["provider"] == "provider_fake_llm"
    assert message_tool_call["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_tool_call["preset"] == "test"


def test_api_backend_template_with_tool_call_and_return_on_tool_response_creates_valid_conversation_and_messages(
    test_config,
    datadir,
):
    backend = make_api_backend(test_config, datadir)
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
    tool_response_metadata = {
        "name": tool_calls[0]["name"],
        "id": tool_calls[0]["id"],
    }
    tool_response_data = {
        "message": "Repeated the word foo 2 times.",
        "result": "foo foo",
    }
    tool_responses = [
        AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "call_4MqKEs9ZWh0qTh0xCFcb9IOI",
                        "type": "tool_calls",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{"word": "foo", "repeats": 2}',
                        },
                    },
                ]
            },
            tool_calls=tool_calls,
        ),
        "Foo repeated twice is: foo foo",
    ]
    overrides = {"request_overrides": fake_llm_responses(tool_responses)}
    success, response, _user_message = backend.run_template(
        "test_template_with_tool_call_and_return_on_tool_response.md", None, overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert len(response["messages"]) == 4
    message_system = response["messages"][0]
    message_user = response["messages"][1]
    message_tool_call = response["messages"][2]
    message_tool_response = response["messages"][3]
    assert message_system["role"] == "system"
    assert message_system["message"] == constants.SYSTEM_MESSAGE_DEFAULT
    assert message_system["message_type"] == "content"
    assert message_system["provider"] == "provider_fake_llm"
    assert message_system["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_system["preset"] == "test"
    assert message_user["role"] == "user"
    assert "template content" in message_user["message"]
    assert message_user["message_type"] == "content"
    assert message_user["provider"] == "provider_fake_llm"
    assert message_user["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_user["preset"] == "test"
    assert message_tool_call["role"] == "assistant"
    assert message_tool_call["message_type"] == "tool_call"
    assert message_tool_call["message_metadata"] is None
    assert message_tool_call["message"] == tool_calls
    assert message_tool_call["provider"] == "provider_fake_llm"
    assert message_tool_call["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_tool_call["preset"] == "test"
    assert message_tool_response["role"] == "tool"
    assert message_tool_response["message_type"] == "tool_response"
    assert message_tool_response["message_metadata"] == tool_response_metadata
    assert message_tool_response["message"] == tool_response_data
    assert message_tool_response["message_type"] == "tool_response"
    assert message_tool_response["provider"] == "provider_fake_llm"
    assert message_tool_response["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_tool_response["preset"] == "test"


def test_api_backend_template_doesnt_override_active_preset_when_preset_in_request_overrides(
    test_config, datadir
):
    backend = make_api_backend(test_config, datadir)
    assert backend.active_preset_name == "test"
    success, response, _user_message = backend.run_template(
        "test_template_doesnt_override_active_preset_when_preset_in_request_overrides.md"
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_assistant = response["messages"][2]
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == "gpt-4o"
    assert message_assistant["preset"] == "test_2"
    assert backend.active_preset_name == "test"


def test_api_backend_template_overrides_active_preset_when_activate_preset_in_request_overrides(
    test_config, datadir
):
    backend = make_api_backend(test_config, datadir)
    assert backend.active_preset_name == "test"
    success, response, _user_message = backend.run_template(
        "test_template_overrides_active_preset_when_activate_preset_in_request_overrides.md"
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_assistant = response["messages"][2]
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == "gpt-4o"
    assert message_assistant["preset"] == "test_2"
    assert backend.active_preset_name == "test_2"


def test_api_backend_template_doesnt_override_system_message_when_system_message_in_request_overrides(
    test_config,
    datadir,
):
    backend = make_api_backend(test_config, datadir)
    assert backend.get_system_message() == constants.SYSTEM_MESSAGE_DEFAULT
    success, response, _user_message = backend.run_template(
        "test_template_doesnt_override_system_message_when_system_message_in_request_overrides.md"
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_system = response["messages"][0]
    assert message_system["role"] == "system"
    assert message_system["message"] == "test system message"
    assert backend.get_system_message() == constants.SYSTEM_MESSAGE_DEFAULT


def test_api_backend_template_sets_custom_title_when_in_request_overrides(test_config, datadir):
    backend = make_api_backend(test_config, datadir)
    success, response, _user_message = backend.run_template(
        "test_template_sets_custom_title_when_in_request_overrides.md"
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert response["conversation"]["title"] == "test custom title"


def test_api_backend_template_overrides_provider_model_when_in_request_overrides(
    test_config, datadir
):
    backend = make_api_backend(test_config, datadir)
    success, response, _user_message = backend.ask("test question")
    assert success
    success, response, _user_message = backend.run_template(
        "test_template_overrides_provider_model_when_in_request_overrides.md"
    )
    assert success
    success, response, _user_message = backend.ask("test question")
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    messages = response["messages"]
    assert messages[0]["provider"] == "provider_fake_llm"
    assert messages[0]["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert messages[1]["provider"] == "provider_fake_llm"
    assert messages[1]["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert messages[2]["provider"] == "provider_fake_llm"
    assert messages[2]["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert messages[3]["provider"] == "provider_fake_llm"
    assert messages[3]["model"] == "gpt-4o"
    assert messages[4]["provider"] == "provider_fake_llm"
    assert messages[3]["model"] == "gpt-4o"
    assert messages[5]["provider"] == "provider_fake_llm"
    assert messages[5]["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert messages[6]["provider"] == "provider_fake_llm"
    assert messages[6]["model"] == constants.API_BACKEND_DEFAULT_MODEL


def test_api_backend_template_include_another_template(test_config, datadir):
    backend = make_api_backend(test_config, datadir)
    success, response, _user_message = backend.run_template(
        "test_template_include_base_template.md"
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_user = response["messages"][1]
    assert message_user["message"] == "Template is included"
