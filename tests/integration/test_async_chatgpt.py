#!/usr/bin/env python

import pytest
import asyncio
from chatgpt_wrapper import AsyncChatGPT
from chatgpt_wrapper.core.config import Config

@pytest.mark.asyncio
async def test_async_chatgpt():
    config = Config(profile='test')
    config.set('backend', 'browser')
    if __name__ == '__main__':
        config.set('browser.debug', True)
    config.set('debug.log.enabled', True)
    gpt = AsyncChatGPT(config)
    bot1 = await gpt.create()
    # bot2 = await gpt.create(browser=bot1.browser)

    response1 = await bot1.ask("Say, bot1!")
    # response2 = await bot2.ask("Say, bot2!")
    print(response1)
    assert response1
    await gpt.cleanup()
    # print(response2)

if __name__ == '__main__':
    asyncio.run(test_async_chatgpt())
