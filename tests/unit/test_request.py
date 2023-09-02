from unittest.mock import MagicMock

from langchain.schema.messages import (
    AIMessage,
    # AIMessageChunk,
)

from lwe.backends.api.request import ApiRequest
from ..base import make_provider


def test_simple_non_streaming_request(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    input = 'test'
    preset = None
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         )
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    success, response_obj, _user_message = request.call_llm(messages)
    assert success is True
    assert response_obj.content == 'test response'


def test_execute_llm_non_streaming_failure_call_llm(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    input = 'test'
    preset = None
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         )
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    request.llm = MagicMock(side_effect=ValueError("Error"))
    success, response_obj, user_message = request.call_llm(messages)
    assert success is False
    assert str(user_message) == "Error"


def test_execute_llm_streaming(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    input = 'test'
    preset = None
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         request_overrides={'stream': True}
                         )
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    success, response_obj, _user_message = request.call_llm(messages)
    assert success is True
    assert response_obj.content == 'test response'


def test_set_request_llm_failure(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    input = 'test'
    preset = None
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         )
    request.extract_metadata_customizations = MagicMock(return_value=(False, None, "Error"))
    success, response, user_message = request.set_request_llm()
    assert success is False
    assert response is None
    assert user_message == "Error"


def test_post_response_function_call(test_config, function_manager, provider_manager, preset_manager):
    provider = make_provider(provider_manager)
    input = 'test'
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
    request = ApiRequest(config=test_config,
                         provider=provider,
                         provider_manager=provider_manager,
                         function_manager=function_manager,
                         input=input,
                         preset=preset,
                         preset_manager=preset_manager,
                         request_overrides=request_overrides
                         )
    request.set_request_llm()
    new_messages, messages = request.prepare_ask_request()
    success, response_obj, user_message = request.call_llm(messages)
    response, new_messages = request.post_response(response_obj, new_messages)
    assert response == {'name': 'test_function', 'arguments': {'word': 'foo'}}
    assert len(new_messages) == 3

    # request = ApiRequest(config=test_config,
    #                      provider=provider,
    #                      provider_manager=provider_manager,
    #                      function_manager=function_manager,
    #                      input=input,
    #                      preset=preset,
    #                      preset_manager=preset_manager,
    #                      system_message=constants.SYSTEM_MESSAGE_DEFAULT,
    #                      old_messages=None,
    #                      max_submission_tokens=constants.OPEN_AI_DEFAULT_MAX_SUBMISSION_TOKENS,
    #                      request_overrides=None,
    #                      return_only=False,
    #                      )
