import pytest

from kira.db.business_repo import BusinessRepository
from kira.errors import ValidationError
from tests.helpers import iso_at, next_business_day


def test_create_pickup_order(repo: BusinessRepository) -> None:
    day = next_business_day()
    order = repo.create_order(
        items=[{"item_type": "product", "item_id": 1, "quantity": 2}],
        pickup_at=iso_at(day, "10:00"),
        customer_name="Ana",
    )
    assert order["folio"].startswith("PED-")
    assert order["fulfillment"] == "pickup"
    assert order["subtotal_cents"] == 9_000_000
    assert order["tax_cents"] == 1_710_000
    assert order["total_cents"] == 10_710_000
    assert order["booking_folio"].startswith("BKG-")
    assert order["quote_folio"].startswith("COT-")
    assert len(order["items"]) == 1


def test_delivery_requires_address(repo: BusinessRepository) -> None:
    day = next_business_day()
    with pytest.raises(ValidationError):
        repo.create_order(
            items=[{"item_type": "product", "item_id": 1, "quantity": 1}],
            pickup_at=iso_at(day, "10:00"),
            customer_name="Ana",
            fulfillment="delivery",
        )


def test_cancel_order_cancels_booking(repo: BusinessRepository) -> None:
    day = next_business_day(5)
    order = repo.create_order(
        items=[{"item_type": "product", "item_id": 1, "quantity": 1}],
        pickup_at=iso_at(day, "10:00"),
        customer_name="Ana",
    )
    cancelled = repo.cancel_booking(order["booking_folio"])
    assert cancelled["status"] == "cancelled"
    found = repo.get_order(order["folio"])
    assert found is not None
    assert found["status"] == "cancelled"
