#!/usr/bin/env python

import asyncio
from chatgpt_wrapper.openai.user import UserManager
from chatgpt_wrapper.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.config import Config

async def main():
    config = Config()
    user_manager = UserManager(config)
    gpt = AsyncOpenAIAPI(config)
    success, user, user_message = user_manager.get_by_user_id(1)
    if success:
        gpt.set_current_user(user)
        success, history, user_message = await gpt.get_history(limit=3)
        if success:
            print("\nHistory:\n")
            for id, conversation in history.items():
                print(conversation['title'])

asyncio.run(main())
