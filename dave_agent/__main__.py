import argparse
import json

from .agent import Agent
from .openai_client import OpenAIClient


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="HAL-9000.local")
    parser.add_argument("--port", default=8002, type=int)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--temp", default=0.2, type=float)
    parser.add_argument("--replyTokens", default=2000, type=int)
    parser.add_argument("--think", choices=["none", "minimal", "low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--system", default="Jesteś przyjaznym agentem. Odpowiadaj zawsze po polsku.")
    return parser.parse_args()


def print_debug(name, value):
    print(f"\n=== {name} ===")
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main():
    args = parse_args()
    client = OpenAIClient(args.host, args.port)
    agent = Agent(client, args.temp, args.replyTokens, args.think, args.system)

    model_info = agent.get_model_info()
    print(model_info)
    if args.debug:
        print_debug("MODELS", model_info)

    while True:
        text = input("user> ")
        if text in {"/exit", "/quit"}:
            break

        last_kind = None
        agent.prepare_user_chat(text)

        if args.debug:
            print_debug("REQUEST", agent.last_request)

        for kind, token in agent.stream_chat():
            if kind != last_kind:
                print(f"\n{kind}> ", end="", flush=True)
                last_kind = kind
            print(token, end="", flush=True)

        print("\n")
        if args.debug:
            print_debug("RESPONSE", agent.last_response)


if __name__ == "__main__":
    main()
