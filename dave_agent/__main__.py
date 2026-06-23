import argparse
import json
from pathlib import Path
import sys

from .agent import Agent
from .config import THINK_LEVELS, load_config
from .openai_client import OpenAIClient
from .tools import ToolRegistry


def parse_args(config):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=config["host"])
    parser.add_argument("--port", default=config["port"], type=int)
    parser.add_argument("--debug", default=config["debug"], action="store_true")
    parser.add_argument("--temp", default=config["temperature"], type=float)
    parser.add_argument("--replyTokens", default=config["reply_tokens"], type=int)
    parser.add_argument("--think", default=config["think"], choices=THINK_LEVELS)
    parser.add_argument("--tools", default=config["tools"])
    parser.add_argument("--system", default=config["system"])
    parser.add_argument("--no-color", action="store_true")
    return parser.parse_args()


class Colors:
    def __init__(self, enabled):
        self.enabled = enabled

    def paint(self, text, code):
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def debug(self, text):
        return self.paint(text, "90")

    def user(self, text):
        return self.paint(text, "36;1")

    def assistant(self, text):
        return self.paint(text, "32;1")

    def reasoning(self, text):
        return self.paint(text, "38;5;244")

    def reasoning_prompt(self, text):
        return self.paint(text, "33")

    def tool(self, text):
        return self.paint(text, "35")


def print_debug(name, value, colors):
    print(colors.debug(f"\n=== {name} ==="))
    print(colors.debug(json.dumps(value, ensure_ascii=False, indent=2)))


def main():
    args = parse_args(load_config())
    colors = Colors(sys.stdout.isatty() and not args.no_color)
    client = OpenAIClient(args.host, args.port)
    tools = ToolRegistry.from_spec(Path.cwd(), args.tools) if args.tools else None
    agent = Agent(client, args.temp, args.replyTokens, args.think, args.system, tools)

    model_info = agent.get_model_info()
    print(colors.debug(str(model_info)))
    if args.debug:
        print_debug("MODELS", model_info, colors)

    while True:
        text = input(colors.user("Dave> "))
        if text in {"/exit", "/quit"}:
            break

        last_kind = None
        agent.prepare_user_chat(text)

        if args.debug:
            print_debug("REQUEST", agent.last_request, colors)

        for kind, token in agent.stream_chat():
            if kind != last_kind:
                if kind == "content":
                    prompt = colors.assistant("HAL-9000> ")
                elif kind == "tool":
                    prompt = colors.tool("tool> ")
                else:
                    prompt = colors.reasoning_prompt("reasoning> ")
                print(f"\n{prompt}", end="", flush=True)
                last_kind = kind
            if kind == "reasoning":
                token = colors.reasoning(token)
            print(token, end="", flush=True)

        print("\n")
        if args.debug:
            print_debug("RESPONSE", agent.last_response, colors)


if __name__ == "__main__":
    main()
