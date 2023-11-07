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

# TODO: Re-enable if https://github.com/langchain-ai/langchain/pull/10200 lands.
# from langchain.chat_models.fake import FakeMessagesListChatModel

from lwe.core.provider import Provider, PresetValue
from lwe.core import constants

# TODO: Remove these definitions if https://github.com/langchain-ai/langchain/pull/10200 lands.
import asyncio
import time
from typing import AsyncIterator, Dict

from langchain.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
)
from langchain.chat_models.base import BaseChatModel
from langchain.schema import ChatResult
from langchain.schema.output import ChatGeneration

# TODO: Remove these definitions if https://github.com/langchain-ai/langchain/pull/10200 lands.

DEFAULT_RESPONSE_MESSAGE = "test response"


class FakeMessagesListChatModel(BaseChatModel):
    responses: Union[List[BaseMessage], List[List[BaseMessage]]]
    sleep: Optional[float] = None
    i: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-messages-list-chat-model"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"responses": self.responses}

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        response = self._call(messages, stop=stop, run_manager=run_manager, **kwargs)
        generation = ChatGeneration(message=response)
        return ChatResult(generations=[generation])

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Union[BaseMessage, List[BaseMessage]]:
        """First try to lookup in queries, else return 'foo' or 'bar'."""
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        return response

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[CallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        for c in response:
            if self.sleep is not None:
                time.sleep(self.sleep)
            yield ChatGenerationChunk(message=c)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[AsyncCallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        for c in response:
            if self.sleep is not None:
                await asyncio.sleep(self.sleep)
            yield ChatGenerationChunk(message=c)


class CustomFakeMessagesListChatModel(FakeMessagesListChatModel):
    model_name: str

    def __init__(self, **kwargs):
        if not kwargs.get("model_name"):
            kwargs["model_name"] = constants.API_BACKEND_DEFAULT_MODEL
        if not kwargs.get("responses"):
            kwargs["responses"] = []
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
            "chat": True,
            "validate_models": False,
            "models": {
                "gpt-3.5-turbo": {
                    "max_tokens": 4096,
                },
                "gpt-3.5-turbo-1106": {
                    "max_tokens": 16384,
                },
                "gpt-4": {
                    "max_tokens": 8192,
                },
            },
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
            "responses": None,
            "model_name": PresetValue(str, options=self.available_models),
        }
