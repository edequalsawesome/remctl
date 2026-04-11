from __future__ import annotations

import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from helpers import load_module


class _DummyHandler:
    def __init__(self, headers=None, body=b"", api_token="secret"):
        self.headers = headers or {}
        self.rfile = io.BytesIO(body)
        self.server = SimpleNamespace(
            api_token=api_token,
            allow_origin=None,
            enable_opengraph=False,
        )
        self.errors = []

    def _error(self, message, status=400):
        self.errors.append((message, status))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_module("remctl_server_test", "remctl-server")

    def test_read_body_parses_json(self):
        handler = _DummyHandler(
            headers={"Content-Length": "16"},
            body=b'{"title":"Test"}',
        )
        body, error_status, error_message = self.server.RemctlHandler._read_body(handler)
        self.assertEqual(body, {"title": "Test"})
        self.assertIsNone(error_status)
        self.assertIsNone(error_message)

    def test_read_body_rejects_oversized_payloads(self):
        handler = _DummyHandler(headers={"Content-Length": str(self.server.MAX_REQUEST_BODY_BYTES + 1)})
        body, error_status, error_message = self.server.RemctlHandler._read_body(handler)
        self.assertIsNone(body)
        self.assertEqual(error_status, 413)
        self.assertIn("too large", error_message.lower())

    def test_check_auth_accepts_valid_bearer_token(self):
        handler = _DummyHandler(headers={"Authorization": "Bearer secret"})
        allowed = self.server.RemctlHandler._check_auth(handler)
        self.assertTrue(allowed)
        self.assertEqual(handler.errors, [])

    def test_check_auth_rejects_invalid_bearer_token(self):
        handler = _DummyHandler(headers={"Authorization": "Bearer wrong"})
        allowed = self.server.RemctlHandler._check_auth(handler)
        self.assertFalse(allowed)
        self.assertEqual(handler.errors, [("Invalid token", 401)])

    def test_internal_error_hides_exception_details(self):
        handler = _DummyHandler()
        handler._log_timing = mock.Mock()
        with mock.patch.object(self.server.sys, "stderr", io.StringIO()) as stderr:
            self.server.RemctlHandler._internal_error(
                handler,
                RuntimeError("database path leaked"),
                "GET",
                "/api/v1/test",
                0.0,
            )
        self.assertEqual(handler.errors, [("Internal server error", 500)])
        handler._log_timing.assert_called_once_with("GET", "/api/v1/test", 500, 0.0)
        self.assertIn("database path leaked", stderr.getvalue())

    def test_bridge_call_skips_sqlite_fallback_when_disabled(self):
        action_data = {"action": "create", "title": "Test reminder"}
        with (
            mock.patch.object(self.server, "ALLOW_UNSAFE_SQLITE_WRITES", False),
            mock.patch.object(self.server, "BRIDGE_PATH", Path("/definitely/not-there")),
            mock.patch.object(self.server, "sqlite_create_reminder") as sqlite_create,
            mock.patch.object(
                self.server,
                "remctl_cli_fallback",
                return_value={"ok": False, "error": "remctl not found"},
            ) as cli_fallback,
        ):
            result = self.server.bridge_call(action_data)

        sqlite_create.assert_not_called()
        cli_fallback.assert_called_once_with(action_data)
        self.assertEqual(result, {"ok": False, "error": "remctl not found"})


if __name__ == "__main__":
    unittest.main()
