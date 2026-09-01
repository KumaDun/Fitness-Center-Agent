from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fitness_agent.env import load_env_file


class EnvFileTests(unittest.TestCase):
    def test_load_env_file_reads_simple_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "\n".join(
                    [
                        "# local settings",
                        "OPENAI_API_KEY='test-key'",
                        'FITNESS_DEMO_USERNAME="Avery-Tan"',
                        "FITNESS_DEMO_PASSWORD=local-password",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                result = load_env_file(path)

                self.assertEqual("test-key", os.environ["OPENAI_API_KEY"])
                self.assertEqual("Avery-Tan", os.environ["FITNESS_DEMO_USERNAME"])
                self.assertEqual("local-password", os.environ["FITNESS_DEMO_PASSWORD"])
                self.assertEqual(("OPENAI_API_KEY", "FITNESS_DEMO_USERNAME", "FITNESS_DEMO_PASSWORD"), result.set_keys)

    def test_load_env_file_overrides_existing_environment_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OPENAI_API_KEY=file-key", encoding="utf-8")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=True):
                result = load_env_file(path)

                self.assertEqual("file-key", os.environ["OPENAI_API_KEY"])
                self.assertEqual(("OPENAI_API_KEY",), result.overwritten_keys)

    def test_load_env_file_can_preserve_existing_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OPENAI_API_KEY=file-key", encoding="utf-8")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=True):
                result = load_env_file(path, override=False)

                self.assertEqual("shell-key", os.environ["OPENAI_API_KEY"])
                self.assertEqual(("OPENAI_API_KEY",), result.preserved_keys)

    def test_load_env_file_replaces_empty_environment_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OPENAI_API_KEY=file-key", encoding="utf-8")

            with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True):
                load_env_file(path)

                self.assertEqual("file-key", os.environ["OPENAI_API_KEY"])


if __name__ == "__main__":
    unittest.main()
