---
description: Template with function call and return on function response
request_overrides:
  preset_overrides:
    metadata:
      return_on_function_response: true
    model_customizations:
      model_kwargs:
        functions:
          - test_function
---

template content
