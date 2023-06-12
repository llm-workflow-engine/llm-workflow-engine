#!/usr/bin/env python

import sys
import time
from lwe import ApiBackend
from lwe.core.config import Config
import lwe.core.util as util

DEFAULT_PROMPT = 'Say five words about earth'

def main(prompt):
    config = Config()
    config.set('debug.log.enabled', True)
    gpt = ApiBackend(config)
    gpt.set_provider_streaming(True)
    temperatures = [t for t, _ in util.float_range_to_completions(0, 2).items()]
    temperatures_list = ", ".join(temperatures)
    temperatures = [float(t) for t in temperatures]
    util.print_markdown(f"# Asking: '{prompt}' at these temperatures:\n{temperatures_list}")
    for temp in temperatures:
        print("")
        util.print_markdown(f"# Temperature: {temp}")
        gpt.provider.set_customization_value('temperature', temp)
        gpt.ask_stream(prompt)
        time.sleep(5)

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    main(prompt)
