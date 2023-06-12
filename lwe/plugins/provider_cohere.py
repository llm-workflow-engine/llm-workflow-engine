from langchain.llms import Cohere

from lwe.core.provider import Provider, PresetValue

COHERE_DEFAULT_MODEL = "base-light"

class ProviderCohere(Provider):

    @property
    def model_property_name(self):
        return 'model'

    @property
    def capabilities(self):
        return {
            'models': {
                'base': {
                    'max_tokens': 2048,
                },
                'base-light': {
                    'max_tokens': 2048,
                },
                'command': {
                    'max_tokens': 4096,
                },
                'command-light': {
                    'max_tokens': 4096,
                },
                'summarize-medium': {
                    'max_tokens': 2048,
                },
                'summarize-xlarge': {
                    'max_tokens': 2048,
                },
            }
        }

    @property
    def default_model(self):
        return COHERE_DEFAULT_MODEL

    def llm_factory(self):
        return Cohere

    def customization_config(self):
        return {
            'model': PresetValue(str, options=self.available_models),
            'max_tokens': PresetValue(int, include_none=True),
            'temperature': PresetValue(float, min_value=0.0, max_value=5.0),
            'k': PresetValue(int, 0, 500),
            'p': PresetValue(float, min_value=0.0, max_value=1.0),
            'frequency_penalty': PresetValue(float, min_value=0.0, max_value=1.0),
            'presence_penalty': PresetValue(float, min_value=0.0, max_value=1.0),
            'truncate': PresetValue(str, options=['NONE', 'START', 'END']),
            'cohere_api_key': PresetValue(str, include_none=True, private=True),
        }
