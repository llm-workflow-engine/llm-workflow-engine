from langchain.chat_models.openai import ChatOpenAI

from chatgpt_wrapper.core.plugin import Plugin

class OpenAIProvider(Plugin):

    def incompatible_backends(self):
        return [
            'chatgpt-browser',
        ]

    def default_config(self):
        return {}

    def setup(self):
        """
        Setup the plugin. This is called by the plugin manager after the backend
        is initialized.
        """
        self.log.info(f"This is OpenAI provider plugin, running with backend: {self.backend.name}")

    def llm_factory(self):
        return ChatOpenAI
