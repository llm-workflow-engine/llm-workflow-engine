from langchain.llms import OpenAI

from chatgpt_wrapper.core.provider import Provider, PresetValue

class ProviderOpenai(Provider):

    @property
    def capabilities(self):
        return {
            'streaming': True,
            'validate_models': False,
            'models': {
                'text-ada-001': {
                    'max_tokens': 2049,
                },
                'text-babbage-001': {
                    'max_tokens': 2049,
                },
                'text-curie-001': {
                    'max_tokens': 2049,
                },
                'text-davinci-001': {
                    'max_tokens': 2049,
                },
                'text-davinci-002': {
                    'max_tokens': 2049,
                },
                'text-davinci-003': {
                    'max_tokens': 2049,
                },
                # NOTE: It appears OpenAI discontinued these models.
                # 'code-davinci-002': {
                #     'max_tokens': 8001,
                # },
                # 'code-davinci-001': {
                #     'max_tokens': 8001,
                # },
                # 'code-cushman-002': {
                #     'max_tokens': 2048,
                # },
                # 'code-cushman-001': {
                #     'max_tokens': 2048,
                # },
            }
        }

    @property
    def default_model(self):
        return 'text-davinci-003'

    def llm_factory(self):
        return OpenAI

    def customization_config(self):
        return {
            'model_name': PresetValue(str, options=self.available_models),
            'temperature': PresetValue(float, min_value=0.0, max_value=2.0),
            'openai_api_key': PresetValue(str, include_none=True, private=True),
            'openai_organization': PresetValue(str, include_none=True, private=True),
            'request_timeout': PresetValue(int),
            'streaming': PresetValue(bool),
            'n': PresetValue(int, 1, 10),
            'max_tokens': PresetValue(int, include_none=True),
            'top_p': PresetValue(float, min_value=0.0, max_value=1.0),
            'frequency_penalty': PresetValue(float, min_value=-2.0, max_value=2.0),
            'presence_penalty': PresetValue(float, min_value=-2.0, max_value=2.0),
            'best_of': PresetValue(int, min_value=1),
            'model_kwargs': {
                'suffix': PresetValue(str, include_none=True),
                'logprobs': PresetValue(int, min_value=1, max_value=5),
                'echo': PresetValue(bool),
                'stop': PresetValue(str, include_none=True),
                'logit_bias': dict,
                'user': PresetValue(str),
            },
        }
