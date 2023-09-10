---
description: Template with function call and return on function call
request_overrides:
  preset_overrides:
    metadata:
      return_on_function_call: true
    model_customizations:
      model_kwargs:
        functions:
          - test_function
---

template content
