from __future__ import annotations

import unittest
from unittest.mock import patch

import main
from fitness_agent.agent import AgentMode


class MainCliTests(unittest.TestCase):
    def test_cli_defaults_to_auto_mode(self) -> None:
        with (
            patch("sys.argv", ["main.py", "What classes are suitable for cardio?"]),
            patch("main.load_env_file"),
            patch("main.FitnessAgentService") as service_class,
            patch("builtins.print"),
        ):
            service_class.return_value.answer.return_value = "answer"

            main.main()

        self.assertEqual(AgentMode.AUTO, service_class.call_args.kwargs["mode"])
        service_class.return_value.answer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
