#!/usr/bin/env python
import logging

from langchain_core.messages import AIMessage, HumanMessage

from ..base import (
    store_conversation_threads,
    fake_llm_responses,
)

from lwe import ApiBackend
from lwe.core import constants

# from lwe.core import util

DEBUG = False


def make_api_backend(test_config, user_id=1):
    if user_id is not None:
        test_config.set("backend_options.default_user", user_id)
    if DEBUG:
        test_config.set("log.console.level", "debug")
        test_config.set("debug.log.enabled", True)
    backend = ApiBackend(test_config)
    if DEBUG:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
    return backend


def test_api_backend_get_history(test_config):
    backend = make_api_backend(test_config)
    store_conversation_threads(backend, rounds=3)
    success, history, user_message = backend.get_history(limit=3)
    if success:
        print("\nHistory:\n")
        for _id, conversation in history.items():
            print(conversation["title"])
    assert success
    assert len(history) == 3


def test_api_backend_non_streaming_valid_response_no_user(test_config):
    backend = make_api_backend(test_config, user_id=None)
    success, response, _user_message = backend.ask("Say hello!")
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert success
    assert response == "test response"
    assert backend.conversation_id is None


def test_api_backend_non_streaming_valid_response_with_user(test_config):
    backend = make_api_backend(test_config)
    success, response, _user_message = backend.ask("Say hello!")
    assert success
    assert response == "test response"
    assert backend.conversation_id == 1


def test_api_backend_message_string_creates_valid_conversation_and_messages(test_config):
    backend = make_api_backend(test_config)
    success, response, _user_message = backend.ask("test question")
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
    assert message_user["message"] == "test question"
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


def test_api_backend_messages_list_creates_valid_conversation_and_messages(test_config):
    backend = make_api_backend(test_config)
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
    success, response, _user_message = backend.ask(messages)
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert response["conversation"]["id"] == 1
    assert response["conversation"]["title"] == "test response"
    assert len(response["messages"]) == 5
    message_system = response["messages"][0]
    message_user = response["messages"][1]
    message_assistant = response["messages"][2]
    message_user_2 = response["messages"][3]
    message_assistant_2 = response["messages"][4]
    assert message_system["role"] == "system"
    assert message_system["message"] == system_message_content
    assert message_system["message_type"] == "content"
    assert message_system["provider"] == "provider_fake_llm"
    assert message_system["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_system["preset"] == "test"
    assert message_user["role"] == "user"
    assert message_user["message"] == user_message_content
    assert message_user["message_type"] == "content"
    assert message_user["provider"] == "provider_fake_llm"
    assert message_user["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_user["preset"] == "test"
    assert message_assistant["role"] == "assistant"
    assert message_assistant["message"] == assistant_message_content
    assert message_assistant["message_type"] == "content"
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_assistant["preset"] == "test"
    assert message_user_2["role"] == "user"
    assert message_user_2["message"] == user_message_content_2
    assert message_user_2["message_type"] == "content"
    assert message_user_2["provider"] == "provider_fake_llm"
    assert message_user_2["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_user_2["preset"] == "test"
    assert message_assistant_2["role"] == "assistant"
    assert message_assistant_2["message"] == "test response"
    assert message_assistant_2["message_type"] == "content"
    assert message_assistant_2["provider"] == "provider_fake_llm"
    assert message_assistant_2["model"] == constants.API_BACKEND_DEFAULT_MODEL
    assert message_assistant_2["preset"] == "test"


def test_api_backend_with_tool_call_creates_valid_conversation_and_messages(test_config):
    backend = make_api_backend(test_config)
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
    request_overrides = {
        "preset_overrides": {
            "model_customizations": {
                "model_kwargs": {
                    "tools": [
                        "test_tool",
                    ],
                },
            },
        },
    }
    request_overrides = fake_llm_responses(tool_responses, request_overrides)
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
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
    assert message_user["message"] == "test question"
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


def test_api_backend_with_tool_call_and_return_on_tool_call_creates_valid_conversation_and_messages(
    test_config,
):
    backend = make_api_backend(test_config)
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
    request_overrides = {
        "preset_overrides": {
            "metadata": {
                "return_on_tool_call": True,
            },
            "model_customizations": {
                "model_kwargs": {
                    "tools": [
                        "test_tool",
                    ],
                },
            },
        },
    }
    request_overrides = fake_llm_responses(tool_responses, request_overrides)
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
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
    assert message_user["message"] == "test question"
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


def test_api_backend_with_tool_call_and_return_on_tool_response_creates_valid_conversation_and_messages(
    test_config,
):
    backend = make_api_backend(test_config)
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
    request_overrides = {
        "preset_overrides": {
            "metadata": {
                "return_on_tool_response": True,
            },
            "model_customizations": {
                "tools": [
                    "test_tool",
                ],
            },
        },
    }
    request_overrides = fake_llm_responses(tool_responses, request_overrides)
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
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
    assert message_user["message"] == "test question"
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


def test_api_backend_sets_active_preset_on_backend_via_config(test_config):
    backend = make_api_backend(test_config, user_id=None)
    assert backend.active_preset_name == "test"
    metadata, customizations = backend.active_preset
    assert metadata["name"] == "test"
    assert customizations == {}


def test_api_backend_doesnt_override_active_preset_when_preset_in_request_overrides(test_config):
    backend = make_api_backend(test_config)
    assert backend.active_preset_name == "test"
    request_overrides = {
        "preset": "test_2",
    }
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_assistant = response["messages"][2]
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == "gpt-4o"
    assert message_assistant["preset"] == "test_2"
    assert backend.active_preset_name == "test"


def test_api_backend_overrides_active_preset_when_activate_preset_in_request_overrides(test_config):
    backend = make_api_backend(test_config)
    assert backend.active_preset_name == "test"
    request_overrides = {
        "preset": "test_2",
        "activate_preset": True,
    }
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_assistant = response["messages"][2]
    assert message_assistant["provider"] == "provider_fake_llm"
    assert message_assistant["model"] == "gpt-4o"
    assert message_assistant["preset"] == "test_2"
    assert backend.active_preset_name == "test_2"


def test_api_backend_doesnt_override_system_message_when_system_message_in_request_overrides(
    test_config,
):
    backend = make_api_backend(test_config)
    assert backend.get_system_message() == constants.SYSTEM_MESSAGE_DEFAULT
    request_overrides = {
        "system_message": "test system message",
    }
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    message_system = response["messages"][0]
    assert message_system["role"] == "system"
    assert message_system["message"] == "test system message"
    assert backend.get_system_message() == constants.SYSTEM_MESSAGE_DEFAULT


def test_api_backend_sets_custom_title_when_in_request_overrides(test_config):
    backend = make_api_backend(test_config)
    request_overrides = {
        "title": "test custom title",
    }
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
    )
    assert success
    success, response, _user_message = backend.get_conversation()
    assert success
    assert response["conversation"]["title"] == "test custom title"


def test_api_backend_overrides_provider_model_when_in_request_overrides(test_config):
    backend = make_api_backend(test_config)
    success, response, _user_message = backend.ask("test question")
    assert success
    request_overrides = {
        "preset_overrides": {
            "model_customizations": {
                "model_name": "gpt-4o",
            },
        },
    }
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
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


def test_api_backend_switches_active_preset_when_switching_conversations(test_config):
    backend = make_api_backend(test_config)
    assert backend.active_preset_name == "test"
    success, response, _user_message = backend.ask("test question")
    assert success
    backend.new_conversation()
    request_overrides = {
        "preset": "test_2",
    }
    success, response, _user_message = backend.ask(
        "test question", request_overrides=request_overrides
    )
    assert success
    assert backend.active_preset_name == "test"
    backend.switch_to_conversation(1)
    assert backend.active_preset_name == "test"
    backend.switch_to_conversation(2)
    assert backend.active_preset_name == "test_2"


def test_api_backend_streaming_with_streaming_callback(test_config):
    stream_response = ""

    def stream_callback(content):
        nonlocal stream_response
        stream_response += content

    backend = make_api_backend(test_config, user_id=None)
    response = ""
    request_overrides = {
        "stream_callback": stream_callback,
    }
    success, response, _user_message = backend.ask_stream(
        "Say three words about earth", request_overrides=request_overrides
    )

    assert success
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert isinstance(response, str)
    assert response == "test response"
    assert stream_response == response


def test_api_backend_streaming_with_print_stream(test_config, capsys):
    backend = make_api_backend(test_config, user_id=None)
    response = ""
    request_overrides = {
        "print_stream": True,
    }
    success, response, _user_message = backend.ask_stream(
        "Say three words about earth", request_overrides=request_overrides
    )

    assert success
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert isinstance(response, str)
    assert response == "test response"
    captured = capsys.readouterr()
    assert "test response" in captured.out


def test_api_backend_with_files(test_config):
    """Test that backend handles files in request_overrides correctly."""
    backend = make_api_backend(test_config)
    file = HumanMessage([{"type": "image", "url": "test.jpg"}])
    request_overrides = {"files": [file]}
    success, response, _user_message = backend.ask("Describe this image", request_overrides=request_overrides)
    assert success is True
    assert response == "test response"
    # Since files cause direct return, no conversation should be created
    assert backend.conversation_id is None


def test_api_backend_with_files_streaming(test_config):
    """Test that backend handles files in request_overrides correctly in streaming mode."""
    backend = make_api_backend(test_config)
    file = HumanMessage([{"type": "image", "url": "test.jpg"}])
    request_overrides = {"files": [file]}
    success, response, _user_message = backend.ask_stream("Describe this image", request_overrides=request_overrides)
    assert success is True
    assert response == "test response"
    # Since files cause direct return, no conversation should be created
    assert backend.conversation_id is None
