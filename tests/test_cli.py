from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from dave import __version__
from dave.cli import main


class FakeApp:
    def __init__(self) -> None:
        self.run_count = 0

    def run(self) -> None:
        self.run_count += 1


class CliTest(unittest.TestCase):
    def test_main_launches_app(self) -> None:
        app = FakeApp()

        exit_code = main([], app_factory=lambda: app)

        self.assertEqual(exit_code, 0)
        self.assertEqual(app.run_count, 1)

    def test_version_does_not_launch_app(self) -> None:
        app = FakeApp()
        stdout = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["--version"], app_factory=lambda: app)

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(stdout.getvalue(), f"dave {__version__}\n")
        self.assertEqual(app.run_count, 0)


if __name__ == "__main__":
    unittest.main()
