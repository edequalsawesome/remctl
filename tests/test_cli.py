from __future__ import annotations

import contextlib
import io
import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from helpers import load_module


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.remctl = load_module("remctl_cli_test", "remctl")

    def test_parse_alarm_normalizes_relative_and_absolute_values(self):
        self.assertEqual(self.remctl.parse_alarm("15m"), "-15m")
        self.assertEqual(self.remctl.parse_alarm("2h"), "-2h")
        self.assertEqual(
            self.remctl.parse_alarm("2026-04-15 14:00"),
            "2026-04-15T14:00:00",
        )

    def test_list_create_uses_bridge_contract_fields(self):
        args = SimpleNamespace(name="Project X", color="blue", json=True)
        with (
            mock.patch.object(self.remctl, "bridge_available", return_value=True),
            mock.patch.object(self.remctl, "bridge_call", return_value={"status": "created"}) as bridge_call,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.remctl.cmd_list_create(args)
        self.assertEqual(
            bridge_call.call_args.args[0],
            {"action": "create_list", "title": "Project X", "color": "blue"},
        )

    def test_list_rename_and_delete_use_bridge_contract_fields(self):
        rename_args = SimpleNamespace(name="Old", new_name="New", json=True)
        delete_args = SimpleNamespace(name="Old", force=True, json=True)
        with (
            mock.patch.object(self.remctl, "bridge_available", return_value=True),
            mock.patch.object(self.remctl, "bridge_call", return_value={"status": "renamed"}) as rename_call,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.remctl.cmd_list_rename(rename_args)
        self.assertEqual(
            rename_call.call_args.args[0],
            {"action": "rename_list", "title": "Old", "newTitle": "New"},
        )

        with (
            mock.patch.object(self.remctl, "bridge_available", return_value=True),
            mock.patch.object(self.remctl, "bridge_call", return_value={"status": "deleted"}) as delete_call,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.remctl.cmd_list_delete(delete_args)
        self.assertEqual(
            delete_call.call_args.args[0],
            {"action": "delete_list", "title": "Old"},
        )

    def test_import_accepts_due_date_from_exported_json(self):
        created_args = []

        def fake_cmd_add(args):
            created_args.append(args)

        payload = [{"title": "Buy milk", "dueDate": "2026-05-01T12:00:00"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "import.json"
            input_path.write_text(json.dumps(payload))
            args = SimpleNamespace(file=str(input_path), json=False)
            with (
                mock.patch.object(self.remctl, "cmd_add", side_effect=fake_cmd_add),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.remctl.cmd_import(args)

        self.assertEqual(len(created_args), 1)
        self.assertEqual(created_args[0].due, "2026-05-01T12:00:00")

    def test_launch_agent_program_args_include_requested_flags(self):
        args = self.remctl.launch_agent_program_args(
            Path("/tmp/remctl-server"),
            host="0.0.0.0",
            port=8123,
            allow_origin="https://example.com",
            enable_opengraph=True,
            allow_unsafe_sqlite_writes=True,
        )
        self.assertEqual(
            args,
            [
                "/tmp/remctl-server",
                "--port",
                "8123",
                "--host",
                "0.0.0.0",
                "--allow-origin",
                "https://example.com",
                "--enable-opengraph",
                "--allow-unsafe-sqlite-writes",
            ],
        )

    def test_parse_launch_agent_settings_supports_legacy_shell_wrapper(self):
        plist = {
            "ProgramArguments": [
                "/bin/zsh",
                "-l",
                "-c",
                "exec /Users/test/bin/remctl-server --port 19876 --host 0.0.0.0",
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            plist_path = Path(tmpdir) / "com.remctl.server.plist"
            with plist_path.open("wb") as fh:
                plistlib.dump(plist, fh)
            with mock.patch.object(self.remctl, "launch_agent_path", return_value=plist_path):
                settings = self.remctl.parse_launch_agent_settings()

        self.assertEqual(settings["server_path"], "/Users/test/bin/remctl-server")
        self.assertEqual(settings["host"], "0.0.0.0")
        self.assertEqual(settings["port"], 19876)

    def test_parse_launch_agent_settings_supports_python_wrapper(self):
        plist = {
            "ProgramArguments": [
                "/usr/bin/python3",
                "/Users/test/bin/remctl-server",
                "--port",
                "19876",
                "--host",
                "0.0.0.0",
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            plist_path = Path(tmpdir) / "com.remctl.server.plist"
            with plist_path.open("wb") as fh:
                plistlib.dump(plist, fh)
            with mock.patch.object(self.remctl, "launch_agent_path", return_value=plist_path):
                settings = self.remctl.parse_launch_agent_settings()

        self.assertEqual(settings["python_path"], "/usr/bin/python3")
        self.assertEqual(settings["server_path"], "/Users/test/bin/remctl-server")
        self.assertEqual(settings["host"], "0.0.0.0")
        self.assertEqual(settings["port"], 19876)

    def test_assess_local_api_probe_flags_degraded_database_as_failure(self):
        result = self.remctl.assess_local_api_probe(
            "127.0.0.1",
            19876,
            {
                "health": {
                    "ok": True,
                    "data": {"status": "degraded", "database": "not found"},
                },
                "stats": None,
                "error": None,
            },
        )
        self.assertEqual(result["status"], "fail")
        self.assertIn("database: not found", result["detail"])

    def test_stop_service_treats_no_such_process_as_already_stopped(self):
        proc = SimpleNamespace(
            returncode=3,
            stdout="",
            stderr="Boot-out failed: 3: No such process",
        )
        with (
            mock.patch.object(self.remctl.sys, "platform", "darwin"),
            mock.patch.object(self.remctl, "launchctl_run", return_value=proc),
        ):
            result = self.remctl.stop_service()
        self.assertTrue(result["ok"])
        self.assertEqual(result["details"], "Service was not loaded")

    def test_resolve_setup_shell_auto_skips_unsupported_shells(self):
        with mock.patch.dict("os.environ", {"SHELL": "/bin/tcsh"}, clear=False):
            self.assertEqual(self.remctl.resolve_setup_shell("auto"), "skip")
        with mock.patch.dict("os.environ", {"SHELL": "/bin/zsh"}, clear=False):
            self.assertEqual(self.remctl.resolve_setup_shell("auto"), "zsh")


if __name__ == "__main__":
    unittest.main()
