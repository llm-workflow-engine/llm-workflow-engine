---
description: Analyze text and provide a positive/negative/neutral sentiment analysis
request_overrides:
  preset: turbo
  preset_overrides:
    model_customizations:
      temperature: 0
---

Perform sentiment analysis on the following text:

```
{{ text }}
```

You should respond with one of three possible sentiments: positive, negative, or neutral. Do not provide any explanation or additional text, only the one word answer based on your analysis.
