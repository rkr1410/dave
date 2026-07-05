from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Protocol

from . import __version__
from dave.runtime.session import Session


class RunnableApp(Protocol):
    def run(self) -> object: ...


AppFactory = Callable[[Session], RunnableApp]


def main(argv: Sequence[str] | None = None, app_factory: AppFactory | None = None) -> int:
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

    session = build_session(args, parser)

    if app_factory is None:
        from dave.ui.textual import DaveTextualApp

        app_factory = DaveTextualApp

    app_factory(session).run()
    return 0


def build_session(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Session:
    if args.fake:
        if args.base_url or args.model or args.api_key:
            parser.error("--fake cannot be combined with --base-url, --model, or --api-key")

        session = Session.fake()
    else:
        if not args.base_url and not args.model and not args.api_key:
            parser.error(
                "choose a provider: use --fake or --base-url URL --model MODEL"
            )
        if not args.base_url or not args.model:
            parser.error("--base-url and --model are required together")

        from dave.providers.openai_compatible import OpenAICompatibleProviderClient

        session = Session(
            model=args.model,
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
