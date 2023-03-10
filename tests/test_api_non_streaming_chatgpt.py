#!/usr/bin/env python

import asyncio
from chatgpt_wrapper.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.config import Config

async def main():
    config = Config()
    gpt = AsyncOpenAIAPI(config)
    success, response, user_message = await gpt.ask("Say hello!")
    if success:
        print("\nRESPONSE:\n")
        print(response)

asyncio.run(main())
