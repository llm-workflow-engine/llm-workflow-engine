import copy

from unittest.mock import Mock

from langchain.schema.messages import (
    AIMessage,
    FunctionMessage,
    # AIMessageChunk,
)

from lwe.core import constants
from lwe.backends.api.request import ApiRequest
from ..base import make_provider

TEST_FUNCTION_CALL_RESPONSE_MESSAGES = [
    {
        "message": "You are a helpful assistant.",
        "message_metadata": None,
        "message_type": "content",
        "role": "system",
    },
    {
        "message": "repeat this word twice: foo",
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
        "message": 'The word "foo" repeated twice is: "foo foo".',
        "message_metadata": None,
        "message_type": "content",
        "role": "assistant",
    },
]


def make_api_request(test_config,
                     function_manager,
                     provider_manager,
                     preset_manager,
                     provider=None,
                     input='test',
                     preset=None,
                     system_message=constants.SYSTEM_MESSAGE_DEFAULT,
                     old_messages=None,
                     max_submission_tokens=constants.OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS,
                     request_overrides=None,
                     return_only=False,
                     ):
    provider = provider or make_provider(provider_manager)
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         system_message=system_message,
                         old_messages=old_messages,
                         max_submission_tokens=max_submission_tokens,
                         request_overrides=request_overrides,
                         return_only=return_only,
                         )
    return request


def test_init_with_defaults(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager, provider)
    assert request.config == test_config
    assert request.provider == provider
    assert request.provider_manager == provider_manager
    assert request.function_manager == function_manager
    assert request.input == 'test'
    assert request.default_preset is None
    assert request.default_preset_name is None
    assert request.preset_manager == preset_manager


def test_init_with_request_overrides(test_config, function_manager, provider_manager, preset_manager):
    request_overrides = {'stream': True}
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager, request_overrides=request_overrides)
    assert request.request_overrides == request_overrides


def test_init_with_preset(test_config, function_manager, provider_manager, preset_manager):
    preset = preset_manager.presets['test']
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager, preset=preset)
    assert request.default_preset == preset
    assert request.default_preset_name == 'test'


def test_set_request_llm_success(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    preset_name = 'test'
    preset_overrides = {'metadata': {'key': 'value'}}
    metadata = {'key': 'value'}
    customizations = {'key': 'value'}
    request.extract_metadata_customizations = Mock(return_value=(True, (preset_name, preset_overrides, metadata, customizations), "Success"))
    llm = Mock()
    request.build_llm = Mock(return_value=(True, llm, "Success"))
    success, response, user_message = request.set_request_llm()
    request.build_llm.call_args.args[0] == preset_name
    request.build_llm.call_args.args[1] == preset_overrides
    request.build_llm.call_args.args[2] == metadata
    request.build_llm.call_args.args[3] == customizations
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


def test_extract_message_content_function_call(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    ai_message = AIMessage(content='', additional_kwargs={'function_call': {'name': 'test_function', 'arguments': '{\n  "one": "test"\n}'}})
    message = request.extract_message_content(ai_message)
    assert message['role'] == 'assistant'
    assert message['message']['name'] == 'test_function'
    assert message['message_type'] == 'function_call'


def test_extract_message_content_function_response(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    function_response = '{"result": "test"}'
    ai_message = FunctionMessage(content=function_response, name="test_function")
    message = request.extract_message_content(ai_message)
    assert message['role'] == 'function'
    assert message['message'] == function_response
    assert message['message_type'] == 'function_response'


def test_extract_message_content_string(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    string_message = 'test_message'
    message = request.extract_message_content(string_message)
    assert message['role'] == 'assistant'
    assert message['message'] == string_message
    assert message['message_type'] == 'content'


def test_should_return_on_function_call(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({'return_on_function_call': True}, {})
    assert request.should_return_on_function_call() is True


def test_check_forced_function(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({}, {'model_kwargs': {'function_call': {}}})
    assert request.check_forced_function() is True


def test_check_return_on_function_response_not_set(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({}, {})
    function_response, new_messages = request.check_return_on_function_response(copy.deepcopy(TEST_FUNCTION_CALL_RESPONSE_MESSAGES))
    assert function_response is None
    assert len(new_messages) == len(TEST_FUNCTION_CALL_RESPONSE_MESSAGES)


def test_check_return_on_function_response_true(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.preset = ({'return_on_function_response': True}, {})
    function_response, new_messages = request.check_return_on_function_response(copy.deepcopy(TEST_FUNCTION_CALL_RESPONSE_MESSAGES))
    assert function_response == {"message": "Repeated the word foo 2 times.", "result": "foo foo"}
    assert len(new_messages) == len(TEST_FUNCTION_CALL_RESPONSE_MESSAGES) - 1


def test_run_function_success(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    run_function_result = {'result': 'test'}
    request.function_manager.run_function = Mock(return_value=(True, run_function_result, 'message'))
    success, json_obj, user_message = request.run_function('test_function', {})
    assert success is True
    assert json_obj == run_function_result


def test_run_function_failure(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.function_manager.run_function = Mock(return_value=(False, None, 'message'))
    success, json_obj, user_message = request.run_function('test_function', {})
    assert success is False
    assert json_obj == {'error': 'message'}


def test_is_function_response_message(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    assert request.is_function_response_message({'message_type': 'function_response'}) is True


def test_terminate_stream(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.streaming = True
    request.terminate_stream(None, None)
    assert request.streaming is False


def test_simple_non_streaming_request(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    success, response_obj, _user_message = request.call_llm(messages)
    assert success is True
    assert response_obj.content == 'test response'


def test_execute_llm_non_streaming_failure_call_llm(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager)
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    request.llm = Mock(side_effect=ValueError("Error"))
    success, response_obj, user_message = request.call_llm(messages)
    assert success is False
    assert str(user_message) == "Error"


def test_execute_llm_streaming(test_config, function_manager, provider_manager, preset_manager):
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager, request_overrides={'stream': True})
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    success, response_obj, _user_message = request.call_llm(messages)
    assert success is True
    assert response_obj.content == 'test response'


def test_post_response_function_call(test_config, function_manager, provider_manager, preset_manager):
    preset = preset_manager.presets['test']
    function_response = AIMessage(content='', additional_kwargs={'function_call': {'name': 'test_function', 'arguments': '{\n  "word": "foo"\n}'}})
    request_overrides = {
        'preset_overrides': {
            'metadata': {
                'return_on_function_call': True,
            },
            'model_customizations': {
                'responses': [
                    function_response,
                ],
            }
        },
    }
    request = make_api_request(test_config, function_manager, provider_manager, preset_manager, preset=preset, request_overrides=request_overrides)
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    success, response_obj, user_message = request.call_llm(messages)
    response, new_messages = request.post_response(response_obj, new_messages)
    assert response == {'name': 'test_function', 'arguments': {'word': 'foo'}}
    assert len(new_messages) == 3
