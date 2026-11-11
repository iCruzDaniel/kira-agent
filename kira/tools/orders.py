"""Tool de creación de pedidos de productos."""

from __future__ import annotations

from typing import Any

from strands import tool

from kira.db.business_repo import BusinessRepository
from kira.tools._common import failure, parse_items


def build_order_tool(repo: BusinessRepository):
    @tool
    def create_order(
        items_json: str,
        pickup_at: str,
        customer_name: str,
        customer_id: str = "",
        customer_phone: str = "",
        fulfillment: str = "pickup",
        delivery_address: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Crea un pedido de productos y reserva el horario de preparación/recogida.

        `items_json` debe ser una lista JSON como:
        [{"item_type": "product", "item_id": 1, "quantity": 2}]

        Args:
            items_json: Lista JSON de productos del pedido.
            pickup_at: Fecha y hora ISO-8601 para recogida o entrega.
            customer_name: Nombre del cliente.
            customer_id: Identificador del cliente, si existe.
            customer_phone: Teléfono de contacto.
            fulfillment: "pickup" para recoger o "delivery" para domicilio.
            delivery_address: Dirección obligatoria si fulfillment es "delivery".
            notes: Notas del pedido.
        """
        try:
            items = parse_items(items_json)
            order = repo.create_order(
                items=items,
                pickup_at=pickup_at,
                customer_name=customer_name,
                customer_id=customer_id,
                customer_phone=customer_phone,
                fulfillment=fulfillment,
                delivery_address=delivery_address,
                notes=notes,
            )
            return {"ok": True, "order": order}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    return create_order
