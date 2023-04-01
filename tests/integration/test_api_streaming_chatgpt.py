#!/usr/bin/env python

import sys
from chatgpt_wrapper.backends.openai.api import OpenAIAPI
from chatgpt_wrapper.core.config import Config

def test_api_streaming():
    config = Config(profile='test')
    config.set('backend', 'chatgpt-api')
    config.set('debug.log.enabled', True)
    gpt = OpenAIAPI(config)
    response = ""
    first = True
    for chunk in gpt.ask_stream("Say three things about earth"):
        if first:
            print("")
            first = False
        print(chunk, end="")
        sys.stdout.flush()
        response += chunk
    print("\n")
    assert response

if __name__ == '__main__':
    test_api_streaming()
