#!/usr/bin/env python

from chatgpt_wrapper.core.config import Config
from chatgpt_wrapper.backends.browser.backend import BrowserBackend

def test_browser_backend_non_streaming():
    config = Config(profile='test')
    if __name__ == '__main__':
        config.set('browser.debug', True)
    config.set('debug.log.enabled', True)
    gpt = BrowserBackend(config)
    gpt.launch_browser()
    success, response1, user_message = gpt.ask("Say, bot1!")
    assert success
    assert response1

if __name__ == '__main__':
    test_browser_backend_non_streaming()
