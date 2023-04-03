#!/usr/bin/env python

from chatgpt_wrapper.backends.openai.api import OpenAIAPI
from chatgpt_wrapper.core.config import Config

def test_api_backend_get_history():
    config = Config(profile='test')
    config.set('debug.log.enabled', True)
    gpt = OpenAIAPI(config, default_user_id=1)
    success, history, user_message = gpt.get_history(limit=3)
    if success:
        print("\nHistory:\n")
        for id, conversation in history.items():
            print(conversation['title'])
    assert success

if __name__ == '__main__':
    test_api_backend_get_history()
