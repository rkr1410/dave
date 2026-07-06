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

    def test_real_provider_launches_app_with_explicit_model(self) -> None:
        launched_apps: list[FakeApp] = []
        detector_calls: list[tuple[str, str | None]] = []

        def make_app(session: Session) -> FakeApp:
            app = FakeApp(session)
            launched_apps.append(app)
            return app

        def detect_model(base_url: str, api_key: str | None) -> str:
            detector_calls.append((base_url, api_key))
            return "detected-model"

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
            model_detector=detect_model,
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
        self.assertEqual(detector_calls, [])

    def test_real_provider_detects_model_when_not_given(self) -> None:
        launched_apps: list[FakeApp] = []
        detector_calls: list[tuple[str, str | None]] = []

        def make_app(session: Session) -> FakeApp:
            app = FakeApp(session)
            launched_apps.append(app)
            return app

        def detect_model(base_url: str, api_key: str | None) -> str:
            detector_calls.append((base_url, api_key))
            return "detected-model"

        exit_code = main(
            [
                "--base-url",
                "http://localhost:8000/v1",
                "--api-key",
                "local-key",
            ],
            app_factory=make_app,
            model_detector=detect_model,
        )

        session = launched_apps[0].session

        self.assertEqual(exit_code, 0)
        self.assertEqual(session.model, "detected-model")
        self.assertIsInstance(session.provider, OpenAICompatibleProviderClient)
        self.assertEqual(detector_calls, [("http://localhost:8000/v1", "local-key")])

    def test_main_requires_provider_choice(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main([], app_factory=lambda session: FakeApp(session))

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("choose a provider", stderr.getvalue())

    def test_model_requires_base_url(self) -> None:
        stderr = io.StringIO()

        with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
            main(["--model", "local-model"], app_factory=FakeApp)

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--base-url is required with --model", stderr.getvalue())

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
