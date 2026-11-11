from datetime import timedelta

import pytest

from kira.config import Settings
from kira.db.business_repo import BusinessRepository
from kira.db.connection import transaction
from kira.errors import ConflictError, PolicyError, ValidationError
from kira.time_utils import iso_utc, now_utc
from tests.helpers import iso_at, next_business_day


def test_book_and_get_appointment(repo: BusinessRepository) -> None:
    day = next_business_day()
    booking = repo.create_booking(
        kind="appointment",
        resource_id=1,
        start_at=iso_at(day, "10:00"),
        customer_name="Ana",
        service_id=1,
    )
    assert booking["folio"].startswith("CIT-")
    assert booking["status"] == "confirmed"
    assert booking["resource_name"] == "Ana"
    assert booking["service_name"] == "Corte clásico"
    found = repo.get_booking(booking["folio"])
    assert found is not None
    assert found["folio"] == booking["folio"]


def test_duplicate_booking_conflicts(repo: BusinessRepository) -> None:
    day = next_business_day()
    start = iso_at(day, "10:00")
    repo.create_booking(
        kind="appointment",
        resource_id=1,
        start_at=start,
        customer_name="Ana",
        service_id=1,
    )
    with pytest.raises(ConflictError):
        repo.create_booking(
            kind="appointment",
            resource_id=1,
            start_at=start,
            customer_name="Luis",
            service_id=1,
        )


def test_cancel_far_future(repo: BusinessRepository) -> None:
    day = next_business_day(5)
    booking = repo.create_booking(
        kind="appointment",
        resource_id=1,
        start_at=iso_at(day, "10:00"),
        customer_name="Ana",
        service_id=1,
    )
    cancelled = repo.cancel_booking(booking["folio"])
    assert cancelled["status"] == "cancelled"


def test_cancel_inside_window_is_rejected(
    repo: BusinessRepository, settings: Settings
) -> None:
    now = now_utc()
    start = now + timedelta(hours=2)
    end = start + timedelta(minutes=30)
    with transaction(settings.db1_path) as conn:
        conn.execute(
            "INSERT INTO bookings(folio, kind, customer_name, resource_id, start_at, end_at, "
            "status, created_at, updated_at) VALUES "
            "('CIT-NEAR', 'appointment', 'Ana', 1, ?, ?, 'confirmed', ?, ?)",
            (iso_utc(start), iso_utc(end), now.isoformat(), now.isoformat()),
        )
    with pytest.raises(PolicyError):
        repo.cancel_booking("CIT-NEAR")


def test_reschedule_appointment(repo: BusinessRepository) -> None:
    day = next_business_day(3)
    booking = repo.create_booking(
        kind="appointment",
        resource_id=1,
        start_at=iso_at(day, "10:00"),
        customer_name="Ana",
        service_id=1,
    )
    updated = repo.reschedule_booking(booking["folio"], iso_at(day, "11:00"))
    assert updated["start_local"].endswith("11:00")


def test_event_booking_uses_room(repo: BusinessRepository) -> None:
    day = next_business_day()
    booking = repo.create_booking(
        kind="event",
        resource_id=3,
        start_at=iso_at(day, "10:00"),
        duration_minutes=60,
        customer_name="Empresa",
        party_size=10,
    )
    assert booking["kind"] == "event"
    assert booking["resource_name"] == "Sala principal"


def test_event_rejects_staff_resource(repo: BusinessRepository) -> None:
    day = next_business_day()
    with pytest.raises(ValidationError):
        repo.create_booking(
            kind="event",
            resource_id=1,
            start_at=iso_at(day, "10:00"),
            duration_minutes=60,
            customer_name="Empresa",
        )
