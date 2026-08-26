"""Small date helpers shared by the stats and report services."""

from datetime import date, timedelta

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_date(raw: str | None, fallback: date | None = None) -> date:
    """Parse a YYYY-MM-DD string, raising ValueError on anything else."""
    if not raw:
        return fallback or date.today()
    from datetime import datetime

    return datetime.strptime(raw, "%Y-%m-%d").date()


def week_start(day: date) -> date:
    """Monday of the week containing ``day``."""
    return day - timedelta(days=day.weekday())


def day_range(start: date, end: date) -> list[date]:
    """Every date from ``start`` to ``end`` inclusive."""
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def percentage(part: int, whole: int) -> int:
    return round(part / whole * 100) if whole else 0
