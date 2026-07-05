"""Manual smoke run for a real OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dave.runtime.events import (
    AssistantMessageAppended,
    ModelResponseFailed,
    RequestApproved,
    RequestRejected,
    UserMessageAppended,
)
from dave.runtime.session import Session, SessionEvent
from dave.runtime.stream_events import (
    ModelResponseFinished,
    ReasoningDelta,
    RequestBuilt,
    RequestSent,
    TextDelta,
)
from dave.providers.openai_compatible import OpenAICompatibleProviderClient

DEFAULT_CONFIG_PATH = Path(__file__).with_suffix(".toml")
DEFAULT_API_KEY = "dummy"


@dataclass
class SmokeConfig:
    base_url: str
    api_key: str
    prompt: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Dave against a real OpenAI-compatible endpoint.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to TOML config. Default: {DEFAULT_CONFIG_PATH}",
    )
    return parser.parse_args()


def load_config(path: Path) -> SmokeConfig:
    with path.open("rb") as file:
        payload = tomllib.load(file)

    return SmokeConfig(
        base_url=require_string(payload, "base_url"),
        api_key=optional_string(payload, "api_key", DEFAULT_API_KEY),
        prompt=require_string(payload, "prompt"),
    )


def require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Config value must be a non-empty string: {key}")
    return value


def optional_string(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Config value must be a non-empty string: {key}")
    return value


def detect_model(config: SmokeConfig) -> str:
    url = f"{config.base_url.rstrip('/')}/models"
    request = Request(
        url,
        headers={"Authorization": f"Bearer {config.api_key}"},
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model discovery failed: HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Model discovery failed: {error.reason}") from error

    model = first_model_id(payload)
    if model is None:
        raise RuntimeError(f"Model discovery returned no usable model id: {payload!r}")
    return model


def first_model_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    for collection_name in ("data", "models"):
        collection = payload.get(collection_name)
        if isinstance(collection, list):
            model = first_model_id_from_collection(collection)
            if model is not None:
                return model

    return None


def first_model_id_from_collection(collection: list[Any]) -> str | None:
    for item in collection:
        if not isinstance(item, dict):
            continue

        for key in ("id", "model", "name"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value

    return None


async def run_smoke(config: SmokeConfig, model: str) -> int:
    print(f"base_url: {config.base_url}")
    print(f"model: {model}")
    print(f"prompt: {config.prompt}")
    print()

    session = Session(
        model=model,
        provider=OpenAICompatibleProviderClient(
            base_url=config.base_url,
            api_key=config.api_key,
        ),
    )

    async for event in session.submit_user_message(config.prompt):
        render_event(event)

    return 0


def render_event(event: SessionEvent) -> None:
    match event:
        case UserMessageAppended(content=content):
            print(f"UserMessageAppended: {content}")
        case RequestBuilt(request=request):
            print(f"RequestBuilt: {len(request.messages)} message(s)")
        case RequestApproved(model=model, message_count=message_count):
            print(f"RequestApproved: model={model} messages={message_count}")
        case RequestSent(request=request):
            print(f"RequestSent: model={request.model}")
        case ReasoningDelta(text=text):
            print(f"ReasoningDelta: {text!r}")
        case TextDelta(text=text):
            print(f"TextDelta: {text!r}")
        case ModelResponseFinished():
            print("ModelResponseFinished")
        case AssistantMessageAppended(content=content):
            print(f"AssistantMessageAppended: {content}")
        case RequestRejected(reason=reason):
            print(f"RequestRejected: {reason}")
        case ModelResponseFailed():
            print("ModelResponseFailed")


async def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    model = detect_model(config)
    return await run_smoke(config, model)


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as error:
        print(f"smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
