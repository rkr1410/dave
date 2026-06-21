from .stream_compactor import StreamCompactor


class Agent:
    def __init__(self, client, temperature, reply_tokens, think, system):
        self.client = client
        self.temperature = temperature
        self.reply_tokens = reply_tokens
        self.think = think
        self.messages = [{"role": "system", "content": system}]
        self.model_info = None
        self.last_request = None
        self.last_response = None

    def get_model_info(self):
        if self.model_info is None:
            self.model_info = self.client.get_model_info()
        return self.model_info

    def prepare_user_chat(self, content):
        self.model_info = self.get_model_info()
        self.messages.append({"role": "user", "content": content})
        self.last_request = self.build_body()
        self.last_response = None

    def stream_chat(self):
        parts = []
        for chunk in self.client.stream_chat(self.last_request):
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            reasoning = delta.get("reasoning")
            if reasoning:
                yield "reasoning", reasoning
            content = delta.get("content")
            if content:
                parts.append(content)
                yield "content", content
        self.messages.append({"role": "assistant", "content": "".join(parts)})
        self.last_response = StreamCompactor.compact(self.client.last_chunks)

    def build_body(self):
        body = {
            "model": self.model_info["model"],
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.reply_tokens,
        }
        if self.think is not None:
            body["reasoning_effort"] = self.think
        return body
