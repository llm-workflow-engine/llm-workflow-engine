---
description: LLM mocks three programmers collaborating step by step to solve a coding challenge and write the final code
request_overrides:
  preset: gpt-4-exploratory-code-writing 
---

Imagine three different expert {{ language[0] | upper }}{{ language[1:] }} programmers are answering the QUESTION below:

1. Each expert will write down step 1 of their thinking, then share it with the group.
2. Then all experts will go on to the next step, and so on.
3. Then they test and debug their programs.
4. If any expert realizes they're wrong at any point then they leave.
5. Debug the final program.

Complete each step and then display the final program code.

QUESTION:

{{ question }}
