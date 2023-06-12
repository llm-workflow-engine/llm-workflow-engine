#!/usr/bin/env python

import time
import sys

from lwe.core.config import Config
from lwe.backends.browser.backend import BrowserBackend

def test_browser_backend_non_streaming(wait=None):
    config = Config(profile='test')
    if __name__ == '__main__':
        config.set('browser.debug', True)
    config.set('debug.log.enabled', True)
    gpt = BrowserBackend(config)
    gpt.launch_browser()
    if wait is not None:
        print(f"Waiting {wait} seconds...")
        time.sleep(wait)
    success, response1, user_message = gpt.ask("Say, bot1!")
    assert success
    assert response1
    if success:
        print(response1)

if __name__ == '__main__':
    wait = int(sys.argv[1]) if len(sys.argv) > 1 else None
    test_browser_backend_non_streaming(wait)
