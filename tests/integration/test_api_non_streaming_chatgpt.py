#!/usr/bin/env python

import pytest
import asyncio
from chatgpt_wrapper.backends.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.core.config import Config

@pytest.mark.asyncio
async def test_api_non_streaming():
    config = Config(profile='test')
    config.set('backend', 'chatgpt-api')
    config.set('debug.log.enabled', True)
    gpt = AsyncOpenAIAPI(config)
    success, response, user_message = await gpt.ask("Say hello!")
    if success:
        print("\nRESPONSE:\n")
        print(response)
    assert success

if __name__ == '__main__':
    asyncio.run(test_api_non_streaming())
