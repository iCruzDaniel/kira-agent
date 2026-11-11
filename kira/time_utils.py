"""Utilidades de fecha y hora con zona horaria explícita."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def get_tz(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def parse_datetime(value: str, tz_name: str) -> datetime:
    """Convierte un ISO-8601 a UTC; si viene sin zona, asume la del negocio."""

    normalized = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_tz(tz_name))
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime, tz_name: str) -> datetime:
    return dt.astimezone(get_tz(tz_name))


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def local_date(value: str, tz_name: str) -> date:
    """Acepta YYYY-MM-DD o un ISO completo y devuelve la fecha local."""

    try:
        return date.fromisoformat(value)
    except ValueError:
        return to_local(parse_datetime(value, tz_name), tz_name).date()


def local_datetime(date_value: date, time_value: str, tz_name: str) -> datetime:
    hour, minute = (int(part) for part in time_value.split(":", 1))
    return datetime.combine(date_value, time(hour, minute), tzinfo=get_tz(tz_name))


def format_local(dt: datetime, tz_name: str) -> str:
    return to_local(dt, tz_name).strftime("%Y-%m-%d %H:%M")
