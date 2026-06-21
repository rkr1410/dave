#!/usr/bin/env python3
import argparse
import json
import urllib.request as http

args = argparse.ArgumentParser()
args.add_argument("--host", default="HAL-9000.local")
args.add_argument("--port", default=8002, type=int)
args.add_argument("--system", required=True)
args = args.parse_args()

base = f"http://{args.host}:{args.port}"
model = json.load(http.urlopen(f"{base}/v1/models"))["data"][0]["id"]
messages = [{"role": "system", "content": args.system}]

while True:
    text = input("user> ")
    if text in {"/exit", "/quit"}:
        break
    messages.append({"role": "user", "content": text})
    body = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 1000}
    req = http.Request(f"{base}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    answer = json.load(http.urlopen(req))["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": answer})
    print(f"assistant> {answer}\n")
