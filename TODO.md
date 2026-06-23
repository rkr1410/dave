* przejść na open-ai

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://HAL-9000.local:8002/v1",
    api_key="EMPTY",
)

model = client.models.list().data[0].id

response = client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=0.2,
    max_tokens=1000,
)

answer = response.choices[0].message.content
```

* ew. nie wiadomo na ile OpenAI ma tryb kompatybilności, może jak dojdzie kolejney 'trcohęinny' model openai-compatible to dorobić pluginy, bo jest jużw 3 miejscach de facto "if deepseek": sprawdzanie max content length streamowanie w agent.py i kompaktowanie
* cutoff na read-file? na pewno dodać rg
* jeśli jakieśdestructive commands, to może side-model na odpytywanie o bezpieczeństwo?