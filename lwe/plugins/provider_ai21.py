from langchain.llms import AI21

from lwe.core.provider import Provider, PresetValue

class ProviderAi21(Provider):

    @property
    def model_property_name(self):
        return 'model'

    @property
    def capabilities(self):
        return {
            'models': {
                'j2-large': {
                    'max_tokens': 8192,
                },
                'j2-grande': {
                    'max_tokens': 8192,
                },
                'j2-jumbo': {
                    'max_tokens': 8192,
                },
                'j2-large-instruct': {
                    'max_tokens': 8192,
                },
                'j2-grande-instruct': {
                    'max_tokens': 8192,
                },
                'j2-jumbo-instruct': {
                    'max_tokens': 8192,
                },
            }
        }

    @property
    def default_model(self):
        return 'j2-jumbo-instruct'

    def llm_factory(self):
        return AI21

    def customization_config(self):
        return {
            'model': PresetValue(str, options=self.available_models),
            'temperature': PresetValue(float, min_value=0.0, max_value=1.0),
            'maxTokens': PresetValue(int, min_value=1),
            'minTokens': PresetValue(int, min_value=0),
            'topP': PresetValue(float, min_value=0.0, max_value=1.0),
            'numResults': PresetValue(int, min_value=1),
            'presencePenalty': {
                'scale': PresetValue(float, min_value=0.0, max_value=5.0),
                'applyToWhitespaces': PresetValue(bool),
                'applyToPunctuations': PresetValue(bool),
                'applyToNumbers': PresetValue(bool),
                'applyToStopwords': PresetValue(bool),
                'applyToEmojis': PresetValue(bool)
            },
            'countPenalty': {
                'scale': PresetValue(float, min_value=0.0, max_value=5.0),
                'applyToWhitespaces': PresetValue(bool),
                'applyToPunctuations': PresetValue(bool),
                'applyToNumbers': PresetValue(bool),
                'applyToStopwords': PresetValue(bool),
                'applyToEmojis': PresetValue(bool)
            },
            'frequencyPenalty': {
                'scale': PresetValue(float, min_value=0.0, max_value=5.0),
                'applyToWhitespaces': PresetValue(bool),
                'applyToPunctuations': PresetValue(bool),
                'applyToNumbers': PresetValue(bool),
                'applyToStopwords': PresetValue(bool),
                'applyToEmojis': PresetValue(bool)
            },
        }
