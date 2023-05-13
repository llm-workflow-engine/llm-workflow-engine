from typing import Optional, List

from pydantic_computed import Computed, computed
from langchain.chat_models.base import BaseChatModel
from langchain.schema import (
    BaseMessage,
    ChatGeneration,
    ChatResult,
)
from langchain.chat_models.openai import _convert_dict_to_message

from chatgpt_wrapper.backends.browser.backend import BrowserBackend
from chatgpt_wrapper.core.provider import Provider, PresetValue

BROWSER_BACKEND_DEFAULT_MODEL = "text-davinci-002-render-sha"

def make_llm_class(klass):
    class BrowserBackendLLM(BaseChatModel):
        streaming: bool = False
        model_name: str = BROWSER_BACKEND_DEFAULT_MODEL
        temperature: float = 0.7
        verbose: bool = False
        browser_backend: Computed[BrowserBackend]

        @property
        def _llm_type(self):
            """Return type of llm."""
            return "chatgpt_browser"

        def dict(self, **kwargs):
            """Return a dictionary of the LLM."""
            starter_dict = dict({'model_name': self.model_name, 'streaming': self.streaming})
            starter_dict["_type"] = self._llm_type
            return starter_dict

        @computed('browser_backend')
        def set_browser_backend(**kwargs):
            return klass

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            model_name = kwargs.get("model_name")
            if model_name:
                self.model_name = model_name

        def _agenerate(self):
            pass

        def _generate(
            self, messages: any, stop: Optional[List[str]] = None, run_manager=None
        ) -> ChatResult:
            prompts = []
            if isinstance(messages, str):
                messages = [messages]
            for message in messages:
                content = message.content if isinstance(message, BaseMessage) else message
                prompts.append(content)
            inner_completion = ""
            role = "assistant"
            for token in self.browser_backend._ask_stream("\n\n".join(prompts)):
                inner_completion += token
                if self.streaming:
                    if run_manager:
                        run_manager.on_llm_new_token(
                            token,
                            verbose=self.verbose,
                        )
            message = _convert_dict_to_message(
                {"content": inner_completion, "role": role}
            )
            generation = ChatGeneration(message=message)
            llm_output = {"model_name": self.model_name}
            return ChatResult(generations=[generation], llm_output=llm_output)

    return BrowserBackendLLM

class ProviderChatgptBrowser(Provider):

    def incompatible_backends(self):
        return [
            'chatgpt-api',
        ]

    @property
    def capabilities(self):
        return {
            'streaming': True,
            'models': {
                'text-davinci-002-render-sha': {
                },
                'text-davinci-002-render-paid': {
                },
                'text-davinci-002-render': {
                },
                'gpt-4': {
                },
                'gpt-4-plugins': {
                    'plugins': True
                },
            }
        }

    @property
    def default_model(self):
        return BROWSER_BACKEND_DEFAULT_MODEL

    def llm_factory(self):
        return make_llm_class(self.backend)

    def customization_config(self):
        return {
            'model_name': PresetValue(str, options=self.available_models),
            'streaming': PresetValue(bool),
        }
