from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Protocol

from . import __version__
from dave.runtime.session import Session


class RunnableApp(Protocol):
    def run(self) -> object: ...


AppFactory = Callable[[Session], RunnableApp]
ModelDetector = Callable[[str, str | None], str]


def main(
    argv: Sequence[str] | None = None,
    app_factory: AppFactory | None = None,
    model_detector: ModelDetector | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="dave",
        description="Dave terminal agent workbench.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"dave {__version__}",
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="run with the deterministic fake provider",
    )
    parser.add_argument("--base-url", help="OpenAI-compatible provider base URL")
    parser.add_argument("--model", help="model name for the OpenAI-compatible provider")
    parser.add_argument("--api-key", help="optional API key for the provider")
    parser.add_argument("--system-prompt", help="optional system prompt")
    args = parser.parse_args(argv)

    session = build_session(args, parser, model_detector=model_detector)

    if app_factory is None:
        from dave.ui.textual import DaveTextualApp

        app_factory = DaveTextualApp

    app_factory(session).run()
    return 0


def build_session(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    model_detector: ModelDetector | None = None,
) -> Session:
    if args.fake:
        if args.base_url or args.model or args.api_key:
            parser.error("--fake cannot be combined with --base-url, --model, or --api-key")

        session = Session.fake()
    else:
        if not args.base_url:
            if args.model or args.api_key:
                parser.error("--base-url is required with --model or --api-key")
            parser.error(
                "choose a provider: use --fake or --base-url URL [--model MODEL]"
            )

        from dave.providers.openai_compatible import (
            OpenAICompatibleProviderClient,
            discover_first_model,
        )

        model_detector = model_detector or discover_first_model
        if args.model:
            model = args.model
        else:
            try:
                model = model_detector(args.base_url, args.api_key)
            except RuntimeError as error:
                parser.error(f"could not detect model; pass --model explicitly: {error}")

        session = Session(
            model=model,
            provider=OpenAICompatibleProviderClient(
                base_url=args.base_url,
                api_key=args.api_key,
            ),
        )

    if args.system_prompt:
        session.set_system_prompt(args.system_prompt)

    return session


if __name__ == "__main__":
    raise SystemExit(main())
