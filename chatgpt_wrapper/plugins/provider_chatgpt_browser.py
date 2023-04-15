from typing import Optional, List

from pydantic_computed import Computed, computed
from langchain.chat_models.base import BaseChatModel
from langchain.schema import (
    BaseMessage,
    ChatGeneration,
    ChatResult,
)
from langchain.chat_models.openai import _convert_dict_to_message

from chatgpt_wrapper.backends.browser.chatgpt import ChatGPT
from chatgpt_wrapper.core.provider import Provider, PresetValue
from chatgpt_wrapper.core import constants

def make_llm_class(klass):
    class ChatGPTLLM(BaseChatModel):
        streaming: bool = False
        model_name: str = "gpt-3.5-turbo"
        temperature: float = 0.7
        verbose: bool = False
        chatgpt: Computed[ChatGPT]

        @computed('chatgpt')
        def set_chatgpt(**kwargs):
            return klass

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            model_name = kwargs.get("model_name")
            if model_name:
                self.model_name = model_name

        def _agenerate(self):
            pass

        def _generate(
            self, messages: any, stop: Optional[List[str]] = None
        ) -> ChatResult:
            prompts = []
            if isinstance(messages, str):
                messages = [messages]
            for message in messages:
                content = message.content if isinstance(message, BaseMessage) else message
                prompts.append(content)
            inner_completion = ""
            role = "assistant"
            for token in self.chatgpt._ask_stream("\n\n".join(prompts)):
                inner_completion += token
                if self.streaming:
                    self.callback_manager.on_llm_new_token(
                        token,
                        verbose=self.verbose,
                    )
            message = _convert_dict_to_message(
                {"content": inner_completion, "role": role}
            )
            generation = ChatGeneration(message=message)
            llm_output = {"model_name": self.model_name}
            return ChatResult(generations=[generation], llm_output=llm_output)

    return ChatGPTLLM

class ProviderChatgptBrowser(Provider):

    def incompatible_backends(self):
        return [
            'chatgpt-api',
        ]

    def llm_factory(self):
        return make_llm_class(self.backend)

    def customization_config(self):
        return {
            'model_name': PresetValue(str, options=constants.RENDER_MODELS.keys()),
        }
