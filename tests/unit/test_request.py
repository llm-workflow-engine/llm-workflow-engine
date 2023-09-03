from unittest.mock import Mock

from langchain.schema.messages import (
    AIMessage,
    # AIMessageChunk,
)

from lwe.core import constants
from lwe.backends.api.request import ApiRequest
from ..base import make_provider


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
