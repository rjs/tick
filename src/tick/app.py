import json
from datetime import date as Date
from pathlib import Path
from zoneinfo import available_timezones

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Input, Label

from tick.config import DEFAULTS
from tick.geo import lookup_timezone
from tick.llm import OllamaError, send_command
from tick.times import compute_hours


class TickApp(App):
    CSS = """
    Label {
        padding: 1 2;
        text-style: bold;
    }
    DataTable {
        margin: 0 2;
    }
    #footer {
        dock: bottom;
        height: auto;
        padding: 0 2;
    }
    #command-input {
        width: 1fr;
    }
    #status-label {
        width: auto;
        padding: 0 1;
    }
    .hidden {
        display: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="date-label")
        yield DataTable(cursor_type="row", zebra_stripes=True)
        with Horizontal(id="footer"):
            yield Input(placeholder="Type a command...", id="command-input")
            yield Label("", id="status-label", classes="hidden")

    def on_mount(self) -> None:
        self.load_defaults()
        self.rebuild_table()

    def _config_path(self) -> Path:
        return Path.home() / ".config" / "tick" / "config.json"

    def _persist_locales(self) -> None:
        path = self._config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.locales, indent=2))

    def load_defaults(self) -> None:
        path = self._config_path()
        if path.exists():
            self.locales = json.loads(path.read_text())
        else:
            self.locales = list(DEFAULTS)
            self._persist_locales()
        self.time_window = Date.today()

    def rebuild_table(self) -> None:
        label = self.query_one("#date-label", Label)
        label.update(self.time_window.strftime("%b %-d, %Y"))

        rows = compute_hours(
            self.locales,
            self.time_window,
            hour_range=24,
            start_hour=0,
        )

        table = self.query_one(DataTable)
        table.clear(columns=True)

        columns = ["Hour (UTC)"] + [loc["name"] for loc in self.locales]
        for col in columns:
            table.add_column(col, key=col)

        for row in rows:
            table.add_row(*row)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""
        self._process_command(event.value)

    @work(thread=True, exclusive=True)
    def _process_command(self, user_input: str) -> None:
        self.call_from_thread(self._show_loading, True)
        try:
            tool_calls = send_command(user_input)
            self.call_from_thread(self._execute_tool_calls, tool_calls)
        except OllamaError as exc:
            self.call_from_thread(self.notify, str(exc), severity="error")
        finally:
            self.call_from_thread(self._show_loading, False)

    def _show_loading(self, visible: bool) -> None:
        label = self.query_one("#status-label", Label)
        if visible:
            label.update("Thinking...")
            label.remove_class("hidden")
        else:
            label.add_class("hidden")

    def _execute_tool_calls(self, tool_calls: list[dict]) -> None:
        locale_tools = {"place_locale", "remove_locale"}
        dispatch = {
            "place_locale": self._handle_place_locale,
            "remove_locale": self._remove_locale,
            "set_time_window": self._set_time_window,
        }
        mutated = False
        for tc in tool_calls:
            handler = dispatch.get(tc["name"])
            if handler:
                handler(**tc["arguments"])
            if tc["name"] in locale_tools:
                mutated = True
        if mutated:
            self._persist_locales()
        self.rebuild_table()

    def _handle_place_locale(self, name: str, iana_tz: str | None = None, after: str | None = None) -> None:
        iana_tz = self._validate_iana_tz(name, iana_tz)
        if iana_tz is None:
            self.notify(f"Could not resolve timezone for '{name}'", severity="warning")
            return

        idx = self._find_locale(name)
        if idx is not None:
            if after is None:
                return  # Already exists, no repositioning requested
            locale = self._extract_locale(idx)
        else:
            locale = self._create_locale(name, iana_tz)

        self._insert_at(locale, after)

    def _extract_locale(self, idx: int) -> dict:
        return self.locales.pop(idx)

    def _create_locale(self, name: str, iana_tz: str) -> dict:
        return {"name": name, "iana_tz": iana_tz}

    def _find_locale(self, name: str) -> int | None:
        return next(
            (i for i, loc in enumerate(self.locales) if loc["name"].lower() == name.lower()),
            None,
        )

    def _insert_at(self, locale: dict, after: str | None) -> None:
        if after is not None and after.upper() == "FIRST":
            self.locales.insert(0, locale)
        elif after is not None:
            idx = self._find_locale(after)
            if idx is not None:
                self.locales.insert(idx + 1, locale)
            else:
                self.locales.append(locale)
        else:
            self.locales.append(locale)

    def _remove_locale(self, name: str) -> None:
        self.locales = [
            loc for loc in self.locales if loc["name"].lower() != name.lower()
        ]

    def _set_time_window(self, date: str) -> None:
        try:
            self.time_window = Date.fromisoformat(date)
        except ValueError:
            self.notify(f"Invalid date: '{date}'", severity="warning")

    def _validate_iana_tz(self, name: str, iana_tz: str | None) -> str | None:
        if iana_tz and iana_tz in available_timezones():
            return iana_tz
        fallback = lookup_timezone(name)
        if fallback and fallback in available_timezones():
            return fallback
        return None
