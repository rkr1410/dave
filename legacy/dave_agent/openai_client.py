import json
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request as http


class OpenAIClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base = f"http://{host}:{port}"
        self.opener = http.build_opener(http.ProxyHandler({}))
        self.last_chunks = []

    def stream_chat(self, request_dict):
        request_dict["stream"] = True
        request_dict.setdefault("stream_options", {"include_usage": True})
        req = self.get_request(request_dict)
        self.last_chunks = []
        with self.open(req) as resp:
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
        with self.open(req) as model_resp:
            resp = json.load(model_resp)
        model_data = resp["data"][0]
        model = model_data.get("id") or model_data.get("model") or model_data.get("name")
        max_context_len = model_data.get("max_model_len")
        if max_context_len is None:
            max_context_len = model_data.get("context_length")
        if max_context_len is None:
            max_context_len = model_data.get("meta", {}).get("n_ctx")
        return {
            "model": model,
            "context_len": max_context_len,
        }

    def open(self, req):
        try:
            return self.opener.open(req)
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as error:
            fallback_req = self.ipv4_fallback_request(req)
            if fallback_req is None:
                return self.curl_open(req, error)
            try:
                return self.opener.open(fallback_req)
            except urllib.error.HTTPError:
                raise
            except urllib.error.URLError as fallback_error:
                return self.curl_open(req, fallback_error)

    def ipv4_fallback_request(self, req):
        if self.is_ipv4_literal(self.host):
            return None

        parsed = urllib.parse.urlsplit(req.full_url)
        try:
            addrs = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)
        except OSError:
            return None
        if not addrs:
            return None

        ipv4 = addrs[0][4][0]
        fallback_url = urllib.parse.urlunsplit(
            (parsed.scheme, f"{ipv4}:{self.port}", parsed.path, parsed.query, parsed.fragment)
        )
        headers = dict(req.header_items())
        headers["Host"] = f"{self.host}:{self.port}"
        return http.Request(fallback_url, req.data, headers, method=req.get_method())

    def is_ipv4_literal(self, host):
        try:
            socket.inet_aton(host)
        except OSError:
            return False
        return host.count(".") == 3

    def curl_open(self, req, original_error):
        cmd = [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--no-buffer",
            "--connect-timeout",
            "10",
            "--noproxy",
            "*",
        ]
        for name, value in req.header_items():
            cmd.extend(["--header", f"{name}: {value}"])
        if req.data is not None:
            cmd.extend(["--request", req.get_method(), "--data-binary", "@-"])
        cmd.append(req.full_url)

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if req.data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as curl_error:
            raise original_error from curl_error

        if req.data is not None:
            process.stdin.write(req.data)
            process.stdin.close()
        return CurlResponse(process, original_error)


class CurlResponse:
    def __init__(self, process, original_error):
        self.process = process
        self.original_error = original_error
        self.stderr = b""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.process.stdout.readline()
        if line:
            return line
        self.check_returncode()
        raise StopIteration

    def read(self, *args):
        data = self.process.stdout.read(*args)
        self.check_returncode()
        return data

    def close(self):
        self.process.stdout.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.collect_stderr()

    def check_returncode(self):
        returncode = self.process.wait()
        self.collect_stderr()
        if returncode != 0:
            detail = self.stderr.decode(errors="replace").strip()
            raise urllib.error.URLError(f"curl fallback failed: {detail}") from self.original_error

    def collect_stderr(self):
        if self.process.stderr.closed:
            return
        self.stderr += self.process.stderr.read()
        self.process.stderr.close()
