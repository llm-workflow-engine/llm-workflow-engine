#!/usr/bin/env python

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper import ApiBackend

def test_api_backend_non_streaming():
    config = Config(profile='test')
    config.set('debug.log.enabled', True)
    gpt = ApiBackend(config)
    success, response, _user_message = gpt.ask("Say hello!")
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert success
    assert isinstance(response, str)

if __name__ == '__main__':
    test_api_backend_non_streaming()
