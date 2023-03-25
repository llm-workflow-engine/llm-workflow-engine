#!/usr/bin/env python

import sys
import asyncio
from chatgpt_wrapper.backends.openai.api import AsyncOpenAIAPI
from chatgpt_wrapper.core.config import Config
import chatgpt_wrapper.core.util as util

DEFAULT_PROMPT = 'Say three things about earth'

async def main(prompt):
    config = Config()
    gpt = AsyncOpenAIAPI(config)
    temperatures = [t for t, _ in util.float_range_to_completions(0, 2).items()]
    temperatures_list = ", ".join(temperatures)
    temperatures = [float(t) for t in temperatures]
    util.print_markdown(f"# Asking: '{prompt}' at these temperatures:\n{temperatures_list}")
    for temp in temperatures:
        util.print_markdown(f"# Temperature: {temp}")
        first = True
        gpt.set_model_temperature(temp)
        async for chunk in gpt.ask_stream(prompt):
            if first:
                print("")
                first = False
            print(chunk, end="")
            sys.stdout.flush()
        print("\n")
        # Work around rate limit if needed.
        await asyncio.sleep(5)

prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
asyncio.run(main(prompt))
