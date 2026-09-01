from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fitness_agent.api.auth import DemoAuthConfig, DemoAuthStore, authenticate, hash_password, verify_password
from fitness_agent.models import Role


class WebAuthTests(unittest.TestCase):
    def test_demo_auth_config_requires_env_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(DemoAuthConfig.from_env())

    def test_demo_auth_config_reads_credentials_from_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "FITNESS_DEMO_USERNAME": "Avery-Tan",
                "FITNESS_DEMO_PASSWORD": "local-password",
                "FITNESS_DEMO_ROLE": "staff",
                "FITNESS_DEMO_STAFF_ID": "staff_001",
            },
            clear=True,
        ):
            config = DemoAuthConfig.from_env()

        self.assertIsNotNone(config)
        assert config is not None
        principal = authenticate("Avery-Tan", "local-password", config)

        self.assertIsNotNone(principal)
        assert principal is not None
        self.assertEqual(Role.STAFF, principal.role)
        self.assertEqual("staff_001", principal.subject_id)

    def test_demo_auth_config_reads_credentials_from_local_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "fitness_agent.local.ini"
            config_path.write_text(
                "\n".join(
                    [
                        "[demo_auth]",
                        "username = Daniel-Lim",
                        "password = local-password",
                        "role = member",
                        "member_id = mem_002",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                config = DemoAuthConfig.from_sources(config_path)

        self.assertIsNotNone(config)
        assert config is not None
        principal = authenticate("Daniel-Lim", "local-password", config)

        self.assertIsNotNone(principal)
        assert principal is not None
        self.assertEqual(Role.MEMBER, principal.role)
        self.assertEqual("mem_002", principal.subject_id)

    def test_demo_auth_store_reads_multiple_local_users(self) -> None:
        encoded = hash_password("local-password", salt="fixed-salt")
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "fitness_agent.local.ini"
            config_path.write_text(
                "\n".join(
                    [
                        "[demo_users]",
                        f"Avery-Tan = password_hash={encoded}, role=member, member_id=mem_001",
                        f"Daniel-Lim = password_hash={encoded}, role=member, member_id=mem_002",
                        f"Maya-Patel = password_hash={encoded}, role=member, member_id=mem_003",
                        f"local-staff = password_hash={encoded}, role=staff, staff_id=staff_001",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                store = DemoAuthStore.from_sources(config_path)

        self.assertIsNotNone(store)
        assert store is not None
        member = authenticate("Avery-Tan", "local-password", store)
        daniel = authenticate("Daniel-Lim", "local-password", store)
        maya = authenticate("Maya-Patel", "local-password", store)
        staff = authenticate("local-staff", "local-password", store)

        self.assertIsNotNone(member)
        self.assertIsNotNone(daniel)
        self.assertIsNotNone(maya)
        self.assertIsNotNone(staff)
        assert member is not None
        assert daniel is not None
        assert maya is not None
        assert staff is not None
        self.assertEqual(Role.MEMBER, member.role)
        self.assertEqual("mem_001", member.subject_id)
        self.assertEqual("mem_002", daniel.subject_id)
        self.assertEqual("mem_003", maya.subject_id)
        self.assertEqual(Role.STAFF, staff.role)
        self.assertEqual("staff_001", staff.subject_id)

    def test_local_config_credentials_override_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "fitness_agent.local.ini"
            config_path.write_text(
                "\n".join(
                    [
                        "[demo_auth]",
                        "username = file-user",
                        "password = file-password",
                        "role = member",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "FITNESS_DEMO_USERNAME": "env-user",
                    "FITNESS_DEMO_PASSWORD": "env-password",
                    "FITNESS_DEMO_ROLE": "staff",
                    "FITNESS_DEMO_STAFF_ID": "staff_001",
                },
                clear=True,
            ):
                config = DemoAuthConfig.from_sources(config_path)

        self.assertIsNotNone(config)
        assert config is not None
        self.assertIsNone(authenticate("env-user", "env-password", config))
        principal = authenticate("file-user", "file-password", config)

        self.assertIsNotNone(principal)
        assert principal is not None
        self.assertEqual(Role.MEMBER, principal.role)

    def test_authenticate_rejects_wrong_password(self) -> None:
        config = DemoAuthConfig("Avery-Tan", None, "local-password", Role.MEMBER, "mem_001", "staff_001")

        self.assertIsNone(authenticate("Avery-Tan", "wrong", config))

    def test_demo_auth_config_rejects_guest_login_role(self) -> None:
        with patch.dict(
            os.environ,
            {
                "FITNESS_DEMO_USERNAME": "Avery-Tan",
                "FITNESS_DEMO_PASSWORD": "local-password",
                "FITNESS_DEMO_ROLE": "guest",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError):
                DemoAuthConfig.from_env()

    def test_password_hash_verification(self) -> None:
        encoded = hash_password("local-password", salt="fixed-salt")

        self.assertTrue(verify_password("local-password", encoded))
        self.assertFalse(verify_password("wrong", encoded))

    def test_demo_auth_config_prefers_password_hash(self) -> None:
        encoded = hash_password("local-password", salt="fixed-salt")
        with patch.dict(
            os.environ,
            {
                "FITNESS_DEMO_USERNAME": "Avery-Tan",
                "FITNESS_DEMO_PASSWORD": "wrong-plaintext",
                "FITNESS_DEMO_PASSWORD_HASH": encoded,
            },
            clear=True,
        ):
            config = DemoAuthConfig.from_env()

        self.assertIsNotNone(config)
        assert config is not None
        self.assertIsNotNone(authenticate("Avery-Tan", "local-password", config))
        self.assertIsNone(authenticate("Avery-Tan", "wrong-plaintext", config))


if __name__ == "__main__":
    unittest.main()
