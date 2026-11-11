from __future__ import annotations

from datetime import date, datetime, time, timedelta

from kira.time_utils import get_tz

TZ = "America/Bogota"


def next_business_day(days_ahead: int = 2) -> date:
    current = datetime.now(get_tz(TZ)).date() + timedelta(days=days_ahead)
    while current.weekday() == 6:
        current += timedelta(days=1)
    return current


def iso_at(day: date, hhmm: str) -> str:
    hour, minute = (int(part) for part in hhmm.split(":", 1))
    return datetime.combine(day, time(hour, minute), tzinfo=get_tz(TZ)).isoformat()
