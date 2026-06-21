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
args.add_argument("--system", required=True)
args = args.parse_args()

base = f"http://{args.host}:{args.port}"
models = json.load(http.urlopen(f"{base}/v1/models"))
model = models["data"][0]["id"]
context_len = models["data"][0]["max_model_len"]
messages = [{"role": "system", "content": args.system}]


def main():
    while True:
        text = input("user> ")
        if text in {"/exit", "/quit"}:
            break
        messages.append({"role": "user", "content": text})
        body = {
            "model": model,
            "messages": messages,
            "temperature": args.temp,
            "max_tokens": args.replyTokens
        }
        if args.think is not None:
            body["reasoning_effort"] = args.think
        if args.debug:
            print(json.dumps(body, ensure_ascii=False, indent=2))
        req = http.Request(f"{base}/v1/chat/completions", json.dumps(body).encode(),
                           {"Content-Type": "application/json"})
        resp = json.load(http.urlopen(req))
        if args.debug:
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        txt_answer = resp["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": txt_answer})
        print(f"assistant> {txt_answer}\n")


def print_welcome_info():
    print(f"\nmodel:   {model}")
    print(f"context: {context_len}\n")


print_welcome_info()
main()
