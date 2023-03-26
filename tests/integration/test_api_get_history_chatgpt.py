#!/usr/bin/env python

import pytest
import asyncio
from chatgpt_wrapper.backends.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.core.config import Config

@pytest.mark.asyncio
async def test_api_get_history():
    config = Config(profile='test')
    config.set('backend', 'chatgpt-api')
    config.set('debug.log.enabled', True)
    gpt = AsyncOpenAIAPI(config, default_user_id=1)
    success, history, user_message = await gpt.get_history(limit=3)
    if success:
        print("\nHistory:\n")
        for id, conversation in history.items():
            print(conversation['title'])
    assert success

if __name__ == '__main__':
    asyncio.run(test_api_get_history())
