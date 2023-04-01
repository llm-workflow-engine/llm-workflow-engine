#!/usr/bin/env python

import sys
import time
from chatgpt_wrapper.backends.openai.api import OpenAIAPI
from chatgpt_wrapper.core.config import Config
import chatgpt_wrapper.core.util as util

DEFAULT_PROMPT = 'Say three things about earth'

def main(prompt):
    config = Config()
    gpt = OpenAIAPI(config)
    temperatures = [t for t, _ in util.float_range_to_completions(0, 2).items()]
    temperatures_list = ", ".join(temperatures)
    temperatures = [float(t) for t in temperatures]
    util.print_markdown(f"# Asking: '{prompt}' at these temperatures:\n{temperatures_list}")
    for temp in temperatures:
        util.print_markdown(f"# Temperature: {temp}")
        first = True
        gpt.set_model_temperature(temp)
        for chunk in gpt.ask_stream(prompt):
            if first:
                print("")
                first = False
            print(chunk, end="")
            sys.stdout.flush()
        print("\n")
        # Work around rate limit if needed.
        time.sleep(5)

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    main(prompt)
