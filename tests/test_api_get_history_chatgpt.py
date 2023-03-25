#!/usr/bin/env python

import asyncio
from chatgpt_wrapper.backends.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.core.config import Config

async def main():
    config = Config()
    config.set('debug.log.enabled', True)
    gpt = AsyncOpenAIAPI(config, default_user_id=1)
    success, history, user_message = await gpt.get_history(limit=3)
    if success:
        print("\nHistory:\n")
        for id, conversation in history.items():
            print(conversation['title'])

asyncio.run(main())
