from typing import Any, Iterator, List, Optional, Union

from langchain.schema.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
)

from langchain.callbacks.manager import (
    CallbackManagerForLLMRun,
)
from langchain.schema.output import ChatGenerationChunk

from langchain.chat_models.fake import FakeMessagesListChatModel

from lwe.core.provider import Provider, PresetValue
from lwe.core import constants

DEFAULT_RESPONSE_MESSAGE = "test response"


class CustomFakeMessagesListChatModel(FakeMessagesListChatModel):
    model_name: str

    def __init__(self, **kwargs):
        if not kwargs.get('model_name'):
            kwargs['model_name'] = constants.API_BACKEND_DEFAULT_MODEL
        if not kwargs.get('responses'):
            kwargs['responses'] = []
        super().__init__(**kwargs)

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        if not self.responses:
            self.responses = [
                AIMessage(content=DEFAULT_RESPONSE_MESSAGE),
            ]
        return super()._call(messages, stop, run_manager, **kwargs)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[CallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        if not self.responses:
            self.responses = [
                [
                    AIMessageChunk(content=DEFAULT_RESPONSE_MESSAGE),
                ],
            ]
        return super()._stream(messages, stop, run_manager, **kwargs)


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
        return CustomFakeMessagesListChatModel

    def customization_config(self):
        return {
            'responses': None,
            'model_name': PresetValue(str, options=self.available_models),
        }
