from __future__ import annotations

import argparse

from . import __version__


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dave",
        description="Dave rewrite scaffold.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"dave {__version__}",
    )
    args, extra = parser.parse_known_args()

    if extra:
        parser.error(
            "this rewrite scaffold does not implement runtime options yet: "
            + " ".join(extra)
        )

    print("Dave rewrite scaffold installed. Runtime implementation has not started yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
