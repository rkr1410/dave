#!/usr/bin/env python3
import json
import sys
import urllib.request as http

URL = "http://HAL-9000.local:8002/v1/chat/completions"
messages = [{"role": "system", "content": sys.argv[1]}]

while True:
    text = input("user> ")
    messages.append({"role": "user", "content": text})
    body = {"model": "google/gemma-4-26b-a4b-it", "messages": messages, "temperature": 0.2, "max_tokens": 1000}
    req = http.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    answer = json.load(http.urlopen(req))["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": answer})
    print(f"assistant> {answer}\n")
