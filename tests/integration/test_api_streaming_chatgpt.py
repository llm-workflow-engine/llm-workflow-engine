#!/usr/bin/env python

import pytest
import sys
import asyncio
from chatgpt_wrapper.backends.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.core.config import Config

@pytest.mark.asyncio
async def test_async_api_streaming():
    config = Config(profile='test')
    config.set('backend', 'chatgpt-api')
    config.set('debug.log.enabled', True)
    gpt = AsyncOpenAIAPI(config)
    response = ""
    first = True
    async for chunk in gpt.ask_stream("Say three things about earth"):
        if first:
            print("")
            first = False
        print(chunk, end="")
        sys.stdout.flush()
        response += chunk
    print("\n")
    assert response

if __name__ == '__main__':
    asyncio.run(test_async_api_streaming())
