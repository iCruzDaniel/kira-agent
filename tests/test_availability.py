import pytest

from kira.db.business_repo import BusinessRepository
from kira.errors import ConflictError, PolicyError
from tests.helpers import iso_at, next_business_day


def test_appointment_slots_start_at_opening(repo: BusinessRepository) -> None:
    day = next_business_day()
    slots = repo.find_available_slots("appointment", day.isoformat(), service_id=1)
    assert slots
    assert slots[0]["start_local"].endswith("09:00")
    assert all(slot["resource_name"] in {"Ana", "Carlos"} for slot in slots)


def test_event_capacity_is_enforced(repo: BusinessRepository) -> None:
    day = next_business_day()
    assert repo.find_available_slots(
        "event", day.isoformat(), duration_minutes=60, party_size=12
    )
    assert (
        repo.find_available_slots(
            "event", day.isoformat(), duration_minutes=60, party_size=13
        )
        == []
    )


def test_booked_slot_is_no_longer_available(repo: BusinessRepository) -> None:
    day = next_business_day()
    slots = repo.find_available_slots("appointment", day.isoformat(), service_id=1)
    slot = slots[0]
    repo.create_booking(
        kind="appointment",
        resource_id=slot["resource_id"],
        start_at=slot["start_at"],
        customer_name="Ana",
        service_id=1,
    )
    remaining = repo.find_available_slots(
        "appointment",
        day.isoformat(),
        service_id=1,
        resource_id=slot["resource_id"],
    )
    assert all(item["start_at"] != slot["start_at"] for item in remaining)
    with pytest.raises(ConflictError):
        repo.check_availability(
            "appointment",
            slot["resource_id"],
            slot["start_at"],
            slot["end_at"],
        )


def test_outside_business_hours_is_rejected(repo: BusinessRepository) -> None:
    day = next_business_day()
    with pytest.raises(PolicyError):
        repo.check_availability(
            "appointment",
            1,
            iso_at(day, "20:00"),
            iso_at(day, "21:00"),
        )
