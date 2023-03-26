#!/usr/bin/env python

from chatgpt_wrapper import ChatGPT
from chatgpt_wrapper.core.config import Config

def test_sync_chatgpt():
    config = Config(profile='test')
    config.set('backend', 'browser')
    if __name__ == '__main__':
        config.set('browser.debug', True)
    config.set('debug.log.enabled', True)
    gpt = ChatGPT(config)
    response1 = gpt.ask("Say, bot1!")
    print(response1)
    assert response1

if __name__ == '__main__':
    test_sync_chatgpt()
