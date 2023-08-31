from langchain.chat_models.fake import FakeListChatModel

from lwe.core.provider import Provider, PresetValue
from lwe.core import constants

DEFAULT_RESPONSES = [
    'test response',
]


class CustomFakeListChatModel(FakeListChatModel):
    model_name: str

    def __init__(self, **kwargs):
        if not kwargs.get('model_name'):
            kwargs['model_name'] = constants.API_BACKEND_DEFAULT_MODEL
        if not kwargs.get('responses'):
            kwargs['responses'] = DEFAULT_RESPONSES
        super().__init__(**kwargs)

class ProviderFakeLlm(Provider):
    """
    Fake LLM provider.
    """

    @property
    def capabilities(self):
        return {
            'chat': True,
            'validate_models': False,
            'models': {
                'gpt-3.5-turbo': {
                    'max_tokens': 4096,
                },
                'gpt-4': {
                    'max_tokens': 8192,
                },
            }
        }

    @property
    def default_model(self):
        return constants.API_BACKEND_DEFAULT_MODEL

    def prepare_messages_method(self):
        return self.prepare_messages_for_llm_chat

    def llm_factory(self):
        return CustomFakeListChatModel

    def customization_config(self):
        return {
            'responses': None,
            'model_name': PresetValue(str, options=self.available_models),
        }
