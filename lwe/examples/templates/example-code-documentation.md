---
description: Code documentation with syntax highlighting, auto-paste from clipboard
request_overrides:
  preset: gpt-4-code-generation
---

Write documentation for this code in the reStructedText format.

Analyze the code to include all arguments and return values in the documentation.

The documentation should ONLY include a brief description of the code, the arguments,
and the return values. Do not include any examples or extended description.

Return the code with the new documentation added, with no other text or explanation.

```{{ syntax_label }}
{{ clipboard }}
```
