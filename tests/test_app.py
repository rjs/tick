import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tick.app import TickApp
from tick.config import DEFAULTS


@pytest.fixture()
def config_path(tmp_path):
    """Patch _config_path to use an isolated tmp directory."""
    path = tmp_path / "config.json"
    with patch.object(TickApp, "_config_path", return_value=path):
        yield path


class TestAppLaunch:
    async def test_app_launches_with_defaults(self, config_path):
        async with TickApp().run_test() as pilot:
            app = pilot.app
            assert len(app.locales) == 3
            assert app.locales[0]["name"] == "Detroit"
            table = app.query_one("DataTable")
            assert table.row_count == 24

    async def test_input_widget_present(self, config_path):
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            assert inp is not None


class TestPersistence:
    async def test_load_defaults_seeds_config_file_when_absent(self, config_path):
        assert not config_path.exists()
        async with TickApp().run_test():
            pass
        assert config_path.exists()
        saved = json.loads(config_path.read_text())
        assert saved == list(DEFAULTS)

    async def test_load_defaults_reads_config_file_when_present(self, config_path):
        custom = [{"name": "Sydney", "iana_tz": "Australia/Sydney"}]
        config_path.write_text(json.dumps(custom))
        async with TickApp().run_test() as pilot:
            assert pilot.app.locales == custom

    @patch("tick.app.send_command")
    async def test_add_locale_persists(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo"}},
        ]
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            inp.value = "add Brasil"
            await inp.action_submit()
            await pilot.pause()

        saved = json.loads(config_path.read_text())
        assert any(loc["name"] == "Brasil" for loc in saved)

    @patch("tick.app.send_command")
    async def test_remove_locale_persists(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "remove_locale", "arguments": {"name": "London"}},
        ]
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            inp.value = "remove London"
            await inp.action_submit()
            await pilot.pause()

        saved = json.loads(config_path.read_text())
        assert not any(loc["name"] == "London" for loc in saved)

    @patch("tick.app.send_command")
    async def test_set_time_window_does_not_persist(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "set_time_window", "arguments": {"date": "2026-02-12"}},
        ]
        async with TickApp().run_test() as pilot:
            # Record mtime after initial seed
            mtime_before = config_path.stat().st_mtime

            inp = pilot.app.query_one("#command-input")
            inp.value = "feb 12"
            await inp.action_submit()
            await pilot.pause()

            mtime_after = config_path.stat().st_mtime
            assert mtime_before == mtime_after


class TestPositioning:
    @patch("tick.app.send_command")
    async def test_add_locale_after_inserts_at_position(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo", "after": "Detroit"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "add Brasil after Detroit"
            await inp.action_submit()
            await pilot.pause()

            assert app.locales[1]["name"] == "Brasil"
            assert len(app.locales) == 4

    @patch("tick.app.send_command")
    async def test_add_locale_after_unknown_appends(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo", "after": "Nonexistent"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "add Brasil after Nonexistent"
            await inp.action_submit()
            await pilot.pause()

            assert app.locales[-1]["name"] == "Brasil"
            assert len(app.locales) == 4

    @patch("tick.app.send_command")
    async def test_move_existing_locale_after(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Tokyo", "iana_tz": "Asia/Tokyo", "after": "Detroit"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "move Tokyo after Detroit"
            await inp.action_submit()
            await pilot.pause()

            names = [loc["name"] for loc in app.locales]
            assert names == ["Detroit", "Tokyo", "London"]

    @patch("tick.app.send_command")
    async def test_move_existing_locale_to_first(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Tokyo", "iana_tz": "Asia/Tokyo", "after": "FIRST"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "move Tokyo to first"
            await inp.action_submit()
            await pilot.pause()

            names = [loc["name"] for loc in app.locales]
            assert names == ["Tokyo", "Detroit", "London"]

    @patch("tick.app.send_command")
    async def test_add_locale_after_first_inserts_at_position_zero(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo", "after": "FIRST"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "add Brasil first"
            await inp.action_submit()
            await pilot.pause()

            assert app.locales[0]["name"] == "Brasil"
            assert len(app.locales) == 4

    @patch("tick.app.send_command")
    async def test_move_locale_persists(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Tokyo", "iana_tz": "Asia/Tokyo", "after": "Detroit"}},
        ]
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            inp.value = "move Tokyo after Detroit"
            await inp.action_submit()
            await pilot.pause()

        saved = json.loads(config_path.read_text())
        names = [loc["name"] for loc in saved]
        assert names == ["Detroit", "Tokyo", "London"]


class TestCommandFlow:
    @patch("tick.app.send_command")
    async def test_input_clears_after_submit(self, mock_send, config_path):
        mock_send.return_value = []
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            inp.value = "hello"
            await inp.action_submit()
            await pilot.pause()
            assert inp.value == ""

    @patch("tick.app.send_command")
    async def test_add_locale_via_tool_call(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Brasil", "iana_tz": "America/Sao_Paulo"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            assert len(app.locales) == 3

            inp = app.query_one("#command-input")
            inp.value = "add Brasil"
            await inp.action_submit()
            await pilot.pause()

            assert len(app.locales) == 4
            assert app.locales[-1]["name"] == "Brasil"
            assert app.locales[-1]["iana_tz"] == "America/Sao_Paulo"

    @patch("tick.app.send_command")
    async def test_remove_locale_via_tool_call(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "remove_locale", "arguments": {"name": "London"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            assert any(loc["name"] == "London" for loc in app.locales)

            inp = app.query_one("#command-input")
            inp.value = "remove London"
            await inp.action_submit()
            await pilot.pause()

            assert not any(loc["name"] == "London" for loc in app.locales)

    @patch("tick.app.send_command")
    async def test_set_time_window_via_tool_call(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "set_time_window", "arguments": {"date": "2026-02-12"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "feb 12"
            await inp.action_submit()
            await pilot.pause()

            from datetime import date
            assert app.time_window == date(2026, 2, 12)

    @patch("tick.app.send_command")
    async def test_duplicate_locale_not_added(self, mock_send, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Detroit", "iana_tz": "America/Detroit"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "add Detroit"
            await inp.action_submit()
            await pilot.pause()

            detroit_count = sum(1 for loc in app.locales if loc["name"] == "Detroit")
            assert detroit_count == 1

    @patch("tick.app.lookup_timezone", return_value="America/Sao_Paulo")
    @patch("tick.app.send_command")
    async def test_add_locale_without_iana_tz(self, mock_send, mock_geo, config_path):
        mock_send.return_value = [
            {"name": "add_locale", "arguments": {"name": "Brasil"}},
        ]
        async with TickApp().run_test() as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "add Brasil"
            await inp.action_submit()
            await pilot.pause()

            assert len(app.locales) == 4
            assert app.locales[-1]["name"] == "Brasil"
            assert app.locales[-1]["iana_tz"] == "America/Sao_Paulo"

    @patch("tick.app.send_command")
    async def test_ollama_error_shows_notification(self, mock_send, config_path):
        from tick.llm import OllamaError
        mock_send.side_effect = OllamaError("connection refused")
        async with TickApp().run_test(notifications=True) as pilot:
            app = pilot.app
            inp = app.query_one("#command-input")
            inp.value = "add Brasil"
            await inp.action_submit()
            await pilot.pause()

            # App should still be functional (locales unchanged)
            assert len(app.locales) == 3
