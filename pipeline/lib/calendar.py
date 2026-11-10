"""Date arithmetic driven by config values and country time zones."""
import calendar
import datetime
from zoneinfo import ZoneInfo


def add_months(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day.day, last))


def parse_instant(value):
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(text)


def local_date(instant, timezone_name):
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=datetime.timezone.utc)
    return instant.astimezone(ZoneInfo(timezone_name)).date()


def stamp(now=None):
    """Build timestamp. Callers pass datetime.now so the value is the build clock."""
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    return now.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat()
