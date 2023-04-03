#!/usr/bin/env python

from chatgpt_wrapper.backends.openai.api import OpenAIAPI
from chatgpt_wrapper.core.config import Config

def test_api_backend_streaming():
    config = Config(profile='test')
    config.set('debug.log.enabled', True)
    gpt = OpenAIAPI(config)
    response = ""
    success, response, _user_message = gpt.ask_stream("Say three things about earth")
    assert success
    assert isinstance(response, str)

if __name__ == '__main__':
    test_api_backend_streaming()
