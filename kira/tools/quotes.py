"""Tools de cotizaciones."""

from __future__ import annotations

from typing import Any

from strands import tool

from kira.db.business_repo import BusinessRepository
from kira.tools._common import failure, parse_items


def build_quote_tools(repo: BusinessRepository) -> list[Any]:
    @tool
    def create_quote(
        items_json: str,
        customer_id: str = "",
        customer_name: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Crea una cotización persistida con folio, impuestos y vigencia.

        `items_json` debe ser una lista JSON como:
        [{"item_type": "service", "item_id": 1, "quantity": 1}]
        donde item_type es "service" o "product".

        Args:
            items_json: Lista JSON de ítems cotizados.
            customer_id: Identificador del cliente, si existe.
            customer_name: Nombre del cliente.
            notes: Notas adicionales para la cotización.
        """
        try:
            items = parse_items(items_json)
            quote = repo.create_quote(items, customer_id, customer_name, notes)
            return {"ok": True, "quote": quote}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    @tool
    def get_quote(folio: str) -> dict[str, Any]:
        """Consulta una cotización por su folio.

        Args:
            folio: Folio de la cotización, por ejemplo COT-20260101-ABC123.
        """
        try:
            quote = repo.get_quote(folio)
            if not quote:
                return {
                    "ok": False,
                    "error": {"code": "not_found", "message": f"No existe la cotización {folio}."},
                }
            return {"ok": True, "quote": quote}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    return [create_quote, get_quote]
