from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from fitness_agent.agent import AgentMode
from fitness_agent.api.app import create_app
from fitness_agent.env import load_env_file


class ApiTests(unittest.TestCase):
    def test_session_chat_and_logout_flow(self) -> None:
        with patch.dict(
            os.environ,
            {
                "FITNESS_DEMO_USERNAME": "Avery-Tan",
                "FITNESS_DEMO_PASSWORD": "local-password",
            },
            clear=True,
        ):
            client = TestClient(create_app(mode=AgentMode.DEMO, load_dotenv=False))

        login = client.post(
            "/api/sessions",
            json={"username": "Avery-Tan", "password": "local-password"},
        )
        self.assertEqual(200, login.status_code)
        token = login.json()["token"]

        session = client.get("/api/session", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, session.status_code)
        self.assertEqual("mem_001", session.json()["subject_id"])

        chat = client.post(
            "/api/chat/messages",
            json={"message": "What classes are open tomorrow in Singapore?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, chat.status_code)
        self.assertIn("Yoga Flow", chat.json()["answer"])

        logout = client.delete("/api/session", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(200, logout.status_code)

        expired = client.get("/api/session", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(401, expired.status_code)

    def test_guest_chat_can_use_public_green_tools(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            client = TestClient(create_app(mode=AgentMode.DEMO, auth_config_path=None, load_dotenv=False))

        response = client.post(
            "/api/chat/messages",
            json={"message": "What classes are open tomorrow in Singapore?"},
        )

        self.assertEqual(200, response.status_code)
        self.assertIn("Yoga Flow", response.json()["answer"])

    def test_guest_chat_cannot_use_personal_tools(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            client = TestClient(create_app(mode=AgentMode.DEMO, auth_config_path=None, load_dotenv=False))

        response = client.post(
            "/api/chat/messages",
            json={"message": "What is my billing balance?"},
        )

        self.assertEqual(200, response.status_code)
        self.assertIn("need to log in", response.json()["answer"])

    def test_guest_chat_uses_client_guest_thread_id(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            app = create_app(mode=AgentMode.DEMO, auth_config_path=None, load_dotenv=False)
            client = TestClient(app)

        with patch.object(app.state.fitness_agent.agent_service, "answer", return_value="guest answer") as answer:
            response = client.post(
                "/api/chat/messages",
                json={"message": "What classes are open?", "guest_thread_id": "browser-guest-1"},
            )

        self.assertEqual(200, response.status_code)
        principal = answer.call_args.args[1]
        self.assertEqual("browser-guest-1", principal.subject_id)

    def test_chat_errors_do_not_leak_runtime_details(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            app = create_app(mode=AgentMode.DEMO, auth_config_path=None, load_dotenv=False)
            client = TestClient(app)

        with (
            patch.object(app.state.fitness_agent.agent_service, "answer", side_effect=RuntimeError("secret stack detail")),
            patch("fitness_agent.api.routes.chat.logger.exception") as logger_exception,
        ):
            response = client.post(
                "/api/chat/messages",
                json={"message": "What classes are open?"},
            )

        self.assertEqual(500, response.status_code)
        self.assertEqual("agent_failed", response.json()["detail"])
        self.assertNotIn("secret stack detail", str(response.json()))
        logger_exception.assert_called_once_with("Agent response failed")

    def test_login_requires_configured_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            client = TestClient(create_app(auth_config_path=None, load_dotenv=False))

        response = client.post("/api/sessions", json={"username": "x", "password": "y"})

        self.assertEqual(503, response.status_code)

    def test_create_app_can_load_openai_key_from_env_file_before_service_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("OPENAI_API_KEY=file-key", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                with patch("fitness_agent.api.app.load_env_file", side_effect=lambda: load_env_file(env_path)):
                    app = create_app()

                self.assertTrue(app.state.fitness_agent.agent_service._should_use_llm())

    def test_config_reports_openai_key_fingerprint_without_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("OPENAI_API_KEY=sk-test-secret-value", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                with patch("fitness_agent.api.app.load_env_file", side_effect=lambda: load_env_file(env_path)):
                    client = TestClient(create_app(auth_config_path=None))

                response = client.get("/api/config")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(
            {"configured": True, "prefix": "sk-test-", "suffix": "alue", "length": 20},
            payload["openai_api_key"],
        )
        self.assertNotIn("sk-test-secret-value", str(payload))
        self.assertIn("OPENAI_API_KEY", payload["env_file"]["set_keys"])


if __name__ == "__main__":
    unittest.main()
