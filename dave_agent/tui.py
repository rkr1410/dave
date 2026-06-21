import argparse
import json
import threading

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from .agent import Agent
from .config import THINK_LEVELS, load_config
from .openai_client import OpenAIClient


def parse_args(config):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=config["host"])
    parser.add_argument("--port", default=config["port"], type=int)
    parser.add_argument("--debug", default=config["debug"], action="store_true")
    parser.add_argument("--temp", default=config["temperature"], type=float)
    parser.add_argument("--replyTokens", default=config["reply_tokens"], type=int)
    parser.add_argument("--think", default=config["think"], choices=THINK_LEVELS)
    parser.add_argument("--system", default=config["system"])
    return parser.parse_args()


class DaveApp(App):
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    Screen {
        layout: vertical;
    }

    #chat {
        height: 1fr;
        padding: 1;
    }

    #prompt {
        dock: bottom;
    }

    .user {
        color: cyan;
        text-style: bold;
    }

    .assistant {
        color: green;
    }

    .reasoning {
        color: yellow;
        text-style: italic;
    }

    .debug {
        color: $text-muted;
    }

    .error {
        color: red;
        text-style: bold;
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, agent, debug):
        super().__init__()
        self.agent = agent
        self.debug_enabled = debug
        self.current_widgets = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="chat")
        yield Input(placeholder="user> ", id="prompt")
        yield Footer()

    def on_mount(self):
        threading.Thread(target=self.load_model_info, daemon=True).start()

    def load_model_info(self):
        try:
            model_info = self.agent.get_model_info()
            self.call_from_thread(self.write_line, f"model: {model_info}", "debug")
            if self.debug_enabled:
                self.call_from_thread(self.write_debug, "MODELS", model_info)
        except Exception as error:
            self.call_from_thread(self.write_line, f"error: {error}", "error")

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        event.input.value = ""

        if not text:
            return
        if text in {"/exit", "/quit"}:
            self.exit()
            return

        event.input.disabled = True
        self.write_line(f"user> {text}", "user")
        threading.Thread(target=self.run_chat, args=(text,), daemon=True).start()

    def run_chat(self, text):
        try:
            self.agent.prepare_user_chat(text)
            if self.debug_enabled:
                self.call_from_thread(self.write_debug, "REQUEST", self.agent.last_request)

            for kind, token in self.agent.stream_chat():
                self.call_from_thread(self.append_stream_token, kind, token)

            if self.debug_enabled:
                self.call_from_thread(self.write_debug, "RESPONSE", self.agent.last_response)
        except Exception as error:
            self.call_from_thread(self.write_line, f"error: {error}", "error")
        finally:
            self.call_from_thread(self.enable_input)

    def append_stream_token(self, kind, token):
        widget = self.current_widgets.get(kind)
        if widget is None:
            widget = Static(f"{kind}> ", classes=kind)
            widget.stream_text = ""
            self.current_widgets[kind] = widget
            self.chat.mount(widget)

        widget.stream_text += token
        widget.update(f"{kind}> {widget.stream_text}")
        self.scroll_chat()

    def write_debug(self, name, value):
        self.write_line(f"=== {name} ===\n{json.dumps(value, ensure_ascii=False, indent=2)}", "debug")

    def write_line(self, text, css_class):
        self.current_widgets = {}
        self.chat.mount(Static(text, classes=css_class))
        self.scroll_chat()

    def enable_input(self):
        prompt = self.query_one("#prompt", Input)
        prompt.disabled = False
        prompt.focus()
        self.current_widgets = {}

    def scroll_chat(self):
        self.chat.scroll_end(animate=False)

    @property
    def chat(self):
        return self.query_one("#chat", VerticalScroll)


def main():
    args = parse_args(load_config())
    client = OpenAIClient(args.host, args.port)
    agent = Agent(client, args.temp, args.replyTokens, args.think, args.system)
    DaveApp(agent, args.debug).run()


if __name__ == "__main__":
    main()
