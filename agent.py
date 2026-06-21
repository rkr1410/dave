#!/usr/bin/env python3
import argparse
import json
import urllib.request as http

args = argparse.ArgumentParser()
args.add_argument("--host", default="HAL-9000.local")
args.add_argument("--port", default=8002, type=int)
args.add_argument("--debug", action="store_true")
args.add_argument("--temp", default=0.2, type=float)
args.add_argument("--replyTokens", default=2000, type=int)
args.add_argument("--think", choices=["none", "minimal", "low", "medium", "high", "xhigh", "max"])
args.add_argument("--system", default="Jesteś przyjaznym agentem. Odpowiadaj zawsze po polsku.")
args = args.parse_args()


class Agent:
    def __init__(self, client, temperature, reply_tokens, think, system):
        self.client = client
        self.temperature = temperature
        self.reply_tokens = reply_tokens
        self.think = think
        self.messages = [{"role": "system", "content": system}]
        self.model_info = None

    def get_model_info(self):
        if self.model_info is None:
            self.model_info = self.client.get_model_info()
        return self.model_info

    def stream_user_chat(self, content):
        self.model_info = self.get_model_info()
        self.messages.append({"role": "user", "content": content})
        body = self.build_body()
        parts = []
        for chunk in self.client.stream_chat(body):
            delta = chunk["choices"][0].get("delta", {})
            reasoning = delta.get("reasoning")
            if reasoning:
                yield "reasoning", reasoning
            content = delta.get("content")
            if content:
                parts.append(content)
                yield "content", content
        self.messages.append({"role": "assistant", "content": "".join(parts)})

    def build_body(self):
        body = {
            "model": self.model_info["model"],
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.reply_tokens
        }
        if self.think is not None:
            body["reasoning_effort"] = self.think
        return body


class OpenAIClient:
    def __init__(self, host, port):
        self.base = f"http://{host}:{port}"

    def stream_chat(self, request_dict):
        request_dict["stream"] = True
        req = self.get_request(request_dict)
        with http.urlopen(req) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ")
                if data == "[DONE]":
                    break
                yield json.loads(data)

    def get_request(self, request_dict):
        return http.Request(
            f"{self.base}/v1/chat/completions",
            json.dumps(request_dict).encode(),
            {"Content-Type": "application/json"},
        )

    def get_model_info(self):
        req = http.Request(f"{self.base}/v1/models")
        resp = json.load(http.urlopen(req))
        return {
            "model": resp["data"][0]["id"],
            "context_len": resp["data"][0]["max_model_len"]
        }

cli = OpenAIClient(args.host, args.port)
agent = Agent(cli, args.temp, args.replyTokens, args.think, args.system)

print(agent.get_model_info())

while True:
    text = input("user> ")
    if text in {"/exit", "/quit"}:
        break
    last_kind = None

    for kind, token in agent.stream_user_chat(text):
        if kind != last_kind:
            print(f"\n{kind}> ", end="", flush=True)
            last_kind = kind
        print(token, end="", flush=True)

    print("\n")

