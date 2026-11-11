import pytest

from kira.db.business_repo import BusinessRepository
from kira.errors import NotFoundError
from kira.tools.quotes import build_quote_tools


def test_create_quote_with_tax(repo: BusinessRepository) -> None:
    quote = repo.create_quote(
        [{"item_type": "service", "item_id": 1, "quantity": 2}],
        customer_id="c1",
        customer_name="Ana",
    )
    assert quote["subtotal_cents"] == 7_000_000
    assert quote["tax_cents"] == 1_330_000
    assert quote["total_cents"] == 8_330_000
    assert quote["folio"].startswith("COT-")
    assert quote["items"][0]["quantity"] == 2
    found = repo.get_quote(quote["folio"])
    assert found is not None
    assert found["total_cents"] == quote["total_cents"]


def test_quote_rejects_unknown_item(repo: BusinessRepository) -> None:
    with pytest.raises(NotFoundError):
        repo.create_quote([{"item_type": "service", "item_id": 999, "quantity": 1}])


def test_quote_tool_returns_structured_error(repo: BusinessRepository) -> None:
    create_quote, _ = build_quote_tools(repo)
    result = create_quote(
        items_json='[{"item_type": "service", "item_id": 999, "quantity": 1}]'
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "not_found"
