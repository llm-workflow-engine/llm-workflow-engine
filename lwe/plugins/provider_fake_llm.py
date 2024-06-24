from typing import Any, Iterator, List, Optional, Union

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
)

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatGenerationChunk

# TODO: Re-enable if https://github.com/langchain-ai/langchain/pull/10200 lands.
# from langchain.chat_models.fake import FakeMessagesListChatModel

from lwe.core.provider import Provider, PresetValue
from lwe.core import constants

# TODO: Remove these definitions if https://github.com/langchain-ai/langchain/pull/10200 lands.
import asyncio
import time
from typing import cast, AsyncIterator, Dict
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessageChunk
from langchain_core.outputs import ChatGeneration, ChatResult

# TODO: Remove these definitions if https://github.com/langchain-ai/langchain/pull/10200 lands.

DEFAULT_RESPONSE_MESSAGE = "test response"


class FakeMessagesListChatModel(BaseChatModel):
    """Fake ChatModel for testing purposes."""

    responses: Union[
        List[Union[BaseMessage, BaseMessageChunk, str]],
        List[List[Union[BaseMessage, BaseMessageChunk, str]]],
    ]
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
        responses = response if isinstance(response, list) else [response]
        generations = [ChatGeneration(message=res) for res in responses]
        return ChatResult(generations=generations)

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Union[BaseMessage, List[BaseMessage]]:
        """Rotate through responses."""
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        if isinstance(response, str):
            response = AIMessage(content=response)
        elif isinstance(response, BaseMessage):
            pass
        elif isinstance(response, list):
            for i, item in enumerate(response):
                if isinstance(item, str):
                    response[i] = AIMessage(content=item)
                elif not isinstance(item, BaseMessage):
                    raise TypeError(f"Unexpected type in response list: {type(item)}")
        else:
            raise TypeError(f"Unexpected type for response: {type(response)}")
        if isinstance(response, BaseMessage):
            return response
        elif isinstance(response, list) and all(isinstance(item, BaseMessage) for item in response):
            return cast(List[BaseMessage], response)
        else:
            raise TypeError("Unexpected type after processing response")

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[CallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Rotate through responses."""
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        for c in response:
            if self.sleep is not None:
                time.sleep(self.sleep)
            if isinstance(c, AIMessageChunk):
                chunk = c
            elif isinstance(c, str):
                chunk = AIMessageChunk(content=c)
            else:
                raise TypeError(f"Unexpected type for response chunk: {type(c)}")
            yield ChatGenerationChunk(message=chunk)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[AsyncCallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Rotate through responses."""
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        for c in response:
            if self.sleep is not None:
                await asyncio.sleep(self.sleep)
            if isinstance(c, AIMessageChunk):
                chunk = c
            elif isinstance(c, str):
                chunk = AIMessageChunk(content=c)
            else:
                raise TypeError(f"Unexpected type for response chunk: {type(c)}")
            yield ChatGenerationChunk(message=chunk)


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


DEFAULT_CAPABILITIES = {
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
        "gpt-4o": {
            "max_tokens": 131072,
        },
    },
}


class ProviderFakeLlm(Provider):
    """
    Fake LLM provider.
    """

    def __init__(self, config=None, **kwargs):
        self._capabilities = DEFAULT_CAPABILITIES
        super().__init__(config, **kwargs)

    @property
    def capabilities(self):
        return self._capabilities

    @capabilities.setter
    def capabilities(self, value):
        self._capabilities = value

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
