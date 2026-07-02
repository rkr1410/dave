from .stream_compactor import StreamCompactor


class Agent:
    def __init__(self, client, temperature, reply_tokens, think, system, tools=None, max_tool_rounds=4):
        self.client = client
        self.temperature = temperature
        self.reply_tokens = reply_tokens
        self.think = think
        self.tools = tools
        self.max_tool_rounds = max_tool_rounds
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
        tool_round = 0
        while True:
            parts = []
            for chunk in self.client.stream_chat(self.last_request):
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                for reasoning_key in StreamCompactor.REASONING_KEYS:
                    reasoning = delta.get(reasoning_key)
                    if reasoning:
                        yield "reasoning", reasoning
                content = delta.get("content")
                if content:
                    parts.append(content)
                    yield "content", content

            self.last_response = StreamCompactor.compact(self.client.last_chunks, self.model_info["model"])
            tool_calls = self.extract_tool_calls(self.last_response)
            assistant_message = {"role": "assistant", "content": "".join(parts)}

            if tool_calls:
                assistant_message["tool_calls"] = tool_calls

            self.messages.append(assistant_message)

            if not tool_calls or self.tools is None:
                break
            if tool_round >= self.max_tool_rounds:
                yield "tool", '{"error": "max tool rounds reached"}'
                break

            for tool_call in tool_calls:
                tool_message = self.tools.run_tool_call(tool_call)
                self.messages.append(tool_message)
                yield "tool", tool_message["content"] + "\n"

            tool_round += 1
            self.last_request = self.build_body()

    def extract_tool_calls(self, response):
        choices = response.get("choices") or []
        if not choices:
            return []

        tool_calls = choices[0].get("delta", {}).get("tool_calls") or []
        return [self.strip_stream_index(tool_call) for tool_call in tool_calls]

    def strip_stream_index(self, tool_call):
        stripped = {key: value for key, value in tool_call.items() if key != "index"}
        if "function" in stripped:
            stripped["function"] = dict(stripped["function"])
        return stripped

    def build_body(self):
        body = {
            "model": self.model_info["model"],
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.reply_tokens,
        }
        if self.think is not None:
            body["reasoning_effort"] = self.think
        if self.tools is not None:
            body["tools"] = self.tools.schemas()
            body["tool_choice"] = "auto"
        return body
