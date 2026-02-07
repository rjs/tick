from datetime import date, datetime, timezone

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Label

from tick.config import DEFAULTS
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
    """

    def compose(self) -> ComposeResult:
        yield Label("", id="date-label")
        yield DataTable(cursor_type="row", zebra_stripes=True)

    def on_mount(self) -> None:
        self.load_defaults()
        self.rebuild_table()

    def load_defaults(self) -> None:
        self.locales = list(DEFAULTS)
        self.time_window = date.today()

    def rebuild_table(self) -> None:
        label = self.query_one("#date-label", Label)
        label.update(self.time_window.strftime("%b %-d, %Y"))

        start_hour = datetime.now(timezone.utc).hour

        rows = compute_hours(
            self.locales,
            self.time_window,
            hour_range=12,
            start_hour=start_hour,
        )

        table = self.query_one(DataTable)
        table.clear(columns=True)

        columns = ["Hour (UTC)"] + [loc["name"] for loc in self.locales]
        for col in columns:
            table.add_column(col, key=col)

        for row in rows:
            table.add_row(*row)
