from langchain.chat_models.openai import ChatOpenAI

from chatgpt_wrapper.core.provider import Provider

class ProviderChatOpenai(Provider):

    def llm_factory(self):
        return ChatOpenAI
