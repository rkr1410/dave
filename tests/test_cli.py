from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout

from dave import __version__
from dave.cli import main
from dave.providers.fake import FakeProviderClient
from dave.providers.openai_compatible import OpenAICompatibleProviderClient
from dave.runtime.messages import SystemMessage
from dave.runtime.session import Session


class FakeApp:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.run_count = 0

    def run(self) -> None:
        self.run_count += 1


class CliTest(unittest.TestCase):
    def test_fake_provider_launches_app(self) -> None:
        launched_apps: list[FakeApp] = []

        def make_app(session: Session) -> FakeApp:
            app = FakeApp(session)
            launched_apps.append(app)
            return app

        exit_code = main(["--fake"], app_factory=make_app)

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(launched_apps), 1)
        self.assertEqual(launched_apps[0].run_count, 1)
        self.assertEqual(launched_apps[0].session.model, "fake")
        self.assertIsInstance(launched_apps[0].session.provider, FakeProviderClient)

    def test_real_provider_launches_app(self) -> None:
        launched_apps: list[FakeApp] = []

        def make_app(session: Session) -> FakeApp:
            app = FakeApp(session)
            launched_apps.append(app)
            return app

        exit_code = main(
            [
                "--base-url",
                "http://localhost:8000/v1",
                "--model",
                "local-model",
                "--api-key",
                "local-key",
                "--system-prompt",
                "be brief",
            ],
            app_factory=make_app,
        )

        session = launched_apps[0].session
        messages = session.build_request().messages

        self.assertEqual(exit_code, 0)
        self.assertEqual(launched_apps[0].run_count, 1)
        self.assertEqual(session.model, "local-model")
        self.assertIsInstance(session.provider, OpenAICompatibleProviderClient)
        self.assertEqual(session.provider.base_url, "http://localhost:8000/v1")
        self.assertEqual(session.provider.api_key, "local-key")
        self.assertEqual(messages, (SystemMessage(content="be brief"),))

    def test_main_requires_provider_choice(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main([], app_factory=lambda session: FakeApp(session))

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("choose a provider", stderr.getvalue())

    def test_base_url_and_model_are_required_together(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["--base-url", "http://localhost:8000/v1"], app_factory=FakeApp)

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--base-url and --model are required together", stderr.getvalue())

    def test_version_does_not_launch_app(self) -> None:
        stdout = io.StringIO()
        launched_apps: list[FakeApp] = []

        def make_app(session: Session) -> FakeApp:
            app = FakeApp(session)
            launched_apps.append(app)
            return app

        with self.assertRaises(SystemExit) as raised, redirect_stdout(stdout):
            main(["--version"], app_factory=make_app)

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(stdout.getvalue(), f"dave {__version__}\n")
        self.assertEqual(launched_apps, [])


if __name__ == "__main__":
    unittest.main()
