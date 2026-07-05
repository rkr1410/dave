from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from typing import Protocol

from . import __version__


class RunnableApp(Protocol):
    def run(self) -> object: ...


AppFactory = Callable[[], RunnableApp]


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
    parser.parse_args(argv)

    if app_factory is None:
        from dave.ui.textual import DaveTextualApp

        app_factory = DaveTextualApp

    app_factory().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
