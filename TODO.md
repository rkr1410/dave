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