from langchain.llms import HuggingFaceHub

from lwe.core.provider import Provider, PresetValue

class ProviderHuggingfaceHub(Provider):

    @property
    def model_property_name(self):
        return 'repo_id'

    @property
    def capabilities(self):
        return {
            'validate_models': False,
            'models': {
                'bert-base-uncased': {
                    'max_tokens': 512,
                },
                'gpt2': {
                    'max_tokens': 512,
                },
                'xlm-roberta-base': {
                    'max_tokens': 512,
                },
                'roberta-base': {
                    'max_tokens': 512,
                },
                'microsoft/layoutlmv3-base': {
                    'max_tokens': 512,
                },
                'distilbert-base-uncased': {
                    'max_tokens': 512,
                },
                't5-base': {
                    'max_tokens': 512,
                },
                'xlm-roberta-large': {
                    'max_tokens': 512,
                },
                'bert-base-cased': {
                    'max_tokens': 512,
                },
                'google/flan-t5-xl': {
                    'max_tokens': 512,
                },
            }
        }

    @property
    def default_model(self):
        return 'gpt2'

    def llm_factory(self):
        return HuggingFaceHub

    def customization_config(self):
        return {
            'repo_id': PresetValue(str, options=self.available_models),
            'model_kwargs': dict,
            'task': PresetValue(str, include_none=True),
        }
