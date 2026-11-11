"""Tool de disponibilidad compartida por citas, eventos y pedidos."""

from __future__ import annotations

from typing import Any

from strands import tool

from kira.db.business_repo import BusinessRepository
from kira.tools._common import failure


def build_availability_tool(repo: BusinessRepository):
    @tool
    def check_availability(
        kind: str,
        date: str,
        service_id: int = 0,
        resource_id: int = 0,
        duration_minutes: int = 0,
        party_size: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Consulta horarios libres para citas, eventos o pedidos.

        Args:
            kind: "appointment" para citas, "event" para eventos, "order" para pedidos.
            date: Fecha local en formato YYYY-MM-DD.
            service_id: Servicio requerido cuando kind es "appointment".
            resource_id: Profesional, sala o punto de recogida; 0 para cualquiera.
            duration_minutes: Duración para eventos o pedidos; en citas se toma del servicio.
            party_size: Número de personas para eventos.
            limit: Máximo de horarios a devolver.
        """
        try:
            slots = repo.find_available_slots(
                kind=kind,
                date_value=date,
                service_id=service_id,
                resource_id=resource_id,
                duration_minutes=duration_minutes,
                party_size=party_size,
                limit=limit,
            )
            message = (
                "Hay horarios disponibles."
                if slots
                else "No hay horarios disponibles con esos criterios."
            )
            return {"ok": True, "message": message, "count": len(slots), "slots": slots}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    return check_availability
