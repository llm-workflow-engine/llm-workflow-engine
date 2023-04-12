from langchain.chat_models.openai import ChatOpenAI

from chatgpt_wrapper.core.provider import Provider, PresetValue
from chatgpt_wrapper.core import constants

class ProviderChatOpenai(Provider):

    def llm_factory(self):
        return ChatOpenAI

    def customization_config(self):
        return {
            'verbose': PresetValue(bool),
            'model_name': PresetValue(str, options=constants.OPENAPI_CHAT_RENDER_MODELS),
            'temperature': PresetValue(float, min_value=0.0, max_value=2.0),
            'model_kwargs': dict,
            'openai_api_key': PresetValue(str, include_none=True, private=True),
            'openai_organization': PresetValue(str, include_none=True, private=True),
            'request_timeout': PresetValue(int),
            'max_retries': PresetValue(int, 1, 10),
            'streaming': PresetValue(bool),
            'n': PresetValue(int, 1, 10),
            'max_tokens': PresetValue(int, include_none=True),
        }
