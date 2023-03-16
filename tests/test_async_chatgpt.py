#!/usr/bin/env python

import asyncio
from chatgpt_wrapper import AsyncChatGPT
from chatgpt_wrapper.config import Config

async def main():
    config = Config()
    config.set('browser.debug', True)
    config.set('debug.log.enabled', True)
    gpt = AsyncChatGPT(config)
    bot1 = await gpt.create()
    #bot2 = await gpt.create(browser=bot1.browser)

    response1 = await bot1.ask("Say, bot1!")
    #response2 = await bot2.ask("Say, bot2!")
    print(response1)
    #print(response2)

asyncio.run(main())
