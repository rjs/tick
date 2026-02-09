from unittest.mock import patch

from tick.app import TickApp


class TestAppLaunch:
    async def test_app_launches_with_defaults(self):
        async with TickApp().run_test() as pilot:
            app = pilot.app
            assert len(app.locales) == 3
            assert app.locales[0]["name"] == "Detroit"
            table = app.query_one("DataTable")
            assert table.row_count == 24

    async def test_input_widget_present(self):
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            assert inp is not None


class TestCommandFlow:
    @patch("tick.app.send_command")
    async def test_input_clears_after_submit(self, mock_send):
        mock_send.return_value = []
        async with TickApp().run_test() as pilot:
            inp = pilot.app.query_one("#command-input")
            inp.value = "hello"
            await inp.action_submit()
            await pilot.pause()
            assert inp.value == ""

    @patch("tick.app.send_command")
    async def test_add_locale_via_tool_call(self, mock_send):
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
    async def test_remove_locale_via_tool_call(self, mock_send):
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
    async def test_set_time_window_via_tool_call(self, mock_send):
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
    async def test_duplicate_locale_not_added(self, mock_send):
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
    async def test_add_locale_without_iana_tz(self, mock_send, mock_geo):
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
    async def test_ollama_error_shows_notification(self, mock_send):
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
