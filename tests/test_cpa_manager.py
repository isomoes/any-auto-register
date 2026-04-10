import unittest
from types import ModuleType
from unittest.mock import patch

from platforms.chatgpt.chatgpt_registration_mode_adapter import (
    CHATGPT_REGISTRATION_MODE_ACCESS_TOKEN_ONLY,
    CHATGPT_REGISTRATION_MODE_REFRESH_TOKEN,
)
from services.cpa_manager import get_cpa_maintenance_config, maintain_cpa_credentials


class _FakeConfigStore:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=""):
        return self._values.get(key, default)


class CpaManagerTests(unittest.TestCase):
    def test_maintenance_mode_defaults_to_legacy_no_rt(self):
        with patch(
            "services.cpa_manager._get_config_store",
            return_value=_FakeConfigStore(),
        ):
            config = get_cpa_maintenance_config()

        self.assertEqual(
            config.chatgpt_registration_mode,
            CHATGPT_REGISTRATION_MODE_ACCESS_TOKEN_ONLY,
        )

    def test_maintenance_register_uses_configured_chatgpt_mode(self):
        config_store = _FakeConfigStore(
            {
                "cpa_cleanup_enabled": "1",
                "cpa_cleanup_threshold": "3",
                "cpa_cleanup_chatgpt_registration_mode": CHATGPT_REGISTRATION_MODE_REFRESH_TOKEN,
            }
        )
        captured = {}
        fake_tasks = ModuleType("api.tasks")

        def _fake_has_active_register_task(*args, **kwargs):
            return False

        def _fake_enqueue(req, source=None, meta=None):
            captured["req"] = req
            captured["source"] = source
            captured["meta"] = meta
            return "task-cpa-auto"

        fake_tasks.has_active_register_task = _fake_has_active_register_task
        fake_tasks.enqueue_register_task = _fake_enqueue
        fake_tasks.RegisterTaskRequest = __import__("collections").namedtuple(
            "RegisterTaskRequest",
            [
                "platform",
                "count",
                "concurrency",
                "register_delay_seconds",
                "executor_type",
                "captcha_solver",
                "extra",
            ],
        )

        with (
            patch("services.cpa_manager._get_config_store", return_value=config_store),
            patch("services.cpa_manager.list_auth_files", return_value=[]),
            patch.dict("sys.modules", {"api.tasks": fake_tasks}),
        ):
            result = maintain_cpa_credentials()

        self.assertTrue(result["register"]["triggered"])
        self.assertEqual(
            captured["req"].extra["chatgpt_registration_mode"],
            CHATGPT_REGISTRATION_MODE_REFRESH_TOKEN,
        )
        self.assertTrue(captured["req"].extra["chatgpt_has_refresh_token_solution"])
        self.assertEqual(
            captured["meta"]["chatgpt_registration_mode"],
            CHATGPT_REGISTRATION_MODE_REFRESH_TOKEN,
        )


if __name__ == "__main__":
    unittest.main()
