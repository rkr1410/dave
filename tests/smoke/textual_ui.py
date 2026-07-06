"""Manual smoke launcher for the Textual UI.

Run from the repo root:

    .venv/bin/python tests/smoke/textual_ui.py
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dave.cli import main as run_dave

DEFAULT_CONFIG_PATH = Path(__file__).with_suffix(".toml")


@dataclass
class TextualSmokeConfig:
    base_url: str
    api_key: str | None = None
    model: str | None = None
    system_prompt: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch Dave Textual UI from a smoke TOML config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to TOML config. Default: {DEFAULT_CONFIG_PATH}",
    )
    return parser.parse_args()


def load_config(path: Path) -> TextualSmokeConfig:
    with path.open("rb") as file:
        payload = tomllib.load(file)

    return TextualSmokeConfig(
        base_url=require_string(payload, "base_url"),
        api_key=optional_string(payload, "api_key"),
        model=optional_string(payload, "model"),
        system_prompt=optional_string(payload, "system_prompt"),
    )


def require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Config value must be a non-empty string: {key}")
    return value


def optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Config value must be a non-empty string: {key}")
    return value


def build_dave_args(config: TextualSmokeConfig) -> list[str]:
    args = ["--base-url", config.base_url]

    if config.api_key is not None:
        args.extend(["--api-key", config.api_key])
    if config.model is not None:
        args.extend(["--model", config.model])
    if config.system_prompt is not None:
        args.extend(["--system-prompt", config.system_prompt])

    return args


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    return run_dave(build_dave_args(config))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"textual smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
