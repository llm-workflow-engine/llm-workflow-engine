#!/usr/bin/env python

import sys
import asyncio
from chatgpt_wrapper.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.config import Config

async def main():
    config = Config()
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

asyncio.run(main())
