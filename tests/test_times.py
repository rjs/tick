from datetime import date

from tick.times import compute_hours


def test_known_conversions():
    """UTC 19:00 on Feb 7 2026 = 2:00 PM Detroit, 7:00 PM London, 4:00 AM+1 Tokyo."""
    locales = [
        {"name": "Detroit", "iana_tz": "America/Detroit"},
        {"name": "London", "iana_tz": "Europe/London"},
        {"name": "Tokyo", "iana_tz": "Asia/Tokyo"},
    ]
    rows = compute_hours(locales, date(2026, 2, 7), hour_range=1, start_hour=19)

    assert len(rows) == 1
    utc_label, detroit, london, tokyo = rows[0]

    assert utc_label == "7:00 PM"
    assert detroit == "2:00 PM"     # UTC-5 (EST)
    assert london == "7:00 PM"      # UTC+0 (GMT)
    assert tokyo == "4:00 AM"       # UTC+9 → next day


def test_twelve_rows():
    locales = [{"name": "London", "iana_tz": "Europe/London"}]
    rows = compute_hours(locales, date(2026, 2, 7), hour_range=12, start_hour=10)
    assert len(rows) == 12


def test_wraps_past_midnight():
    """Hours that wrap past midnight should still produce valid times."""
    locales = [{"name": "London", "iana_tz": "Europe/London"}]
    rows = compute_hours(locales, date(2026, 2, 7), hour_range=6, start_hour=22)

    assert len(rows) == 6
    # First row is 10 PM UTC, last is 3 AM UTC next day
    assert rows[0][0] == "10:00 PM"
    assert rows[5][0] == "3:00 AM"
