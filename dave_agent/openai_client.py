import json
import urllib.request as http


class OpenAIClient:
    def __init__(self, host, port):
        self.base = f"http://{host}:{port}"
        self.last_chunks = []

    def stream_chat(self, request_dict):
        request_dict["stream"] = True
        request_dict.setdefault("stream_options", {"include_usage": True})
        req = self.get_request(request_dict)
        self.last_chunks = []
        with http.urlopen(req) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ")
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                self.last_chunks.append(chunk)
                yield chunk

    def get_request(self, request_dict):
        return http.Request(
            f"{self.base}/v1/chat/completions",
            json.dumps(request_dict).encode(),
            {"Content-Type": "application/json"},
        )

    def get_model_info(self):
        req = http.Request(f"{self.base}/v1/models")
        resp = json.load(http.urlopen(req))
        model = resp["data"][0].get("id")
        max_context_len = resp["data"][0].get("max_model_len")
        if max_context_len is None:
            max_context_len = resp["data"][0].get("context_length")
        return {
            "model": model,
            "context_len": max_context_len,
        }
