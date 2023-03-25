#!/usr/bin/env python

import asyncio
from chatgpt_wrapper.backends.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.core.config import Config

async def main():
    config = Config()
    config.set('debug.log.enabled', True)
    gpt = AsyncOpenAIAPI(config)
    success, response, user_message = await gpt.ask("Say hello!")
    if success:
        print("\nRESPONSE:\n")
        print(response)

asyncio.run(main())
