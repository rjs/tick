from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def compute_hours(
    locales: list[dict],
    time_window: date,
    hour_range: int = 12,
    start_hour: int | None = None,
) -> list[list[str]]:
    """Convert a range of UTC hours into local times for each locale.

    Returns a list of rows. Each row is [utc_label, tz1_time, tz2_time, ...].
    """
    if start_hour is None:
        start_hour = datetime.now(timezone.utc).hour

    rows = []
    for offset in range(hour_range):
        utc_hour = (start_hour + offset) % 24
        day_offset = (start_hour + offset) // 24
        utc_dt = datetime(
            time_window.year,
            time_window.month,
            time_window.day,
            utc_hour,
            tzinfo=timezone.utc,
        )
        # Advance date if we wrapped past midnight
        from datetime import timedelta

        utc_dt = utc_dt + timedelta(days=day_offset)

        utc_label = utc_dt.strftime("%-I:%M %p")

        row = [utc_label]
        for locale in locales:
            tz = ZoneInfo(locale["iana_tz"])
            local_dt = utc_dt.astimezone(tz)
            row.append(local_dt.strftime("%-I:%M %p"))
        rows.append(row)

    return rows
