"""Tools de agenda: citas, eventos, consulta, cancelación y reagendado."""

from __future__ import annotations

from typing import Any

from strands import tool

from kira.db.business_repo import BusinessRepository
from kira.errors import ValidationError
from kira.time_utils import iso_utc, local_date, parse_datetime
from kira.tools._common import failure


def _pick_appointment_resource(
    repo: BusinessRepository, service_id: int, start_at: str
) -> int:
    day = local_date(start_at, repo.tz_name).isoformat()
    slots = repo.find_available_slots("appointment", day, service_id=service_id, limit=100)
    target = iso_utc(parse_datetime(start_at, repo.tz_name))
    for slot in slots:
        if slot["start_at"] == target:
            return int(slot["resource_id"])
    return 0


def build_booking_tools(repo: BusinessRepository) -> list[Any]:
    @tool
    def book_appointment(
        service_id: int,
        start_at: str,
        customer_name: str,
        customer_id: str = "",
        customer_phone: str = "",
        resource_id: int = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        """Agenda una cita para un servicio.

        Args:
            service_id: ID del servicio a agendar.
            start_at: Fecha y hora ISO-8601, por ejemplo 2026-11-12T10:00:00-05:00.
            customer_name: Nombre del cliente.
            customer_id: Identificador del cliente, si existe.
            customer_phone: Teléfono de contacto.
            resource_id: Profesional preferido; 0 para asignar el primero disponible.
            notes: Notas para la cita.
        """
        try:
            chosen = resource_id or _pick_appointment_resource(repo, service_id, start_at)
            if not chosen:
                raise ValidationError(
                    "No hay disponibilidad para ese servicio en la fecha y hora solicitadas."
                )
            booking = repo.create_booking(
                kind="appointment",
                resource_id=chosen,
                start_at=start_at,
                customer_name=customer_name,
                customer_id=customer_id,
                customer_phone=customer_phone,
                service_id=service_id,
                notes=notes,
            )
            return {"ok": True, "booking": booking}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    @tool
    def book_event(
        start_at: str,
        duration_minutes: int,
        customer_name: str,
        party_size: int = 1,
        customer_id: str = "",
        customer_phone: str = "",
        resource_id: int = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        """Agenda un evento en una sala.

        Args:
            start_at: Fecha y hora ISO-8601 de inicio.
            duration_minutes: Duración del evento en minutos.
            customer_name: Nombre del cliente o responsable.
            party_size: Número de asistentes.
            customer_id: Identificador del cliente, si existe.
            customer_phone: Teléfono de contacto.
            resource_id: Sala preferida; 0 para elegir una con capacidad suficiente.
            notes: Notas del evento.
        """
        try:
            chosen = resource_id
            if not chosen:
                rooms = [
                    room
                    for room in repo.list_resources("room")
                    if int(room["seats"]) >= party_size
                ]
                if not rooms:
                    raise ValidationError(
                        f"No hay salas con capacidad para {party_size} personas."
                    )
                chosen = int(rooms[0]["id"])
            booking = repo.create_booking(
                kind="event",
                resource_id=chosen,
                start_at=start_at,
                customer_name=customer_name,
                customer_id=customer_id,
                customer_phone=customer_phone,
                duration_minutes=duration_minutes,
                party_size=party_size,
                notes=notes,
            )
            return {"ok": True, "booking": booking}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    @tool
    def get_booking(folio: str) -> dict[str, Any]:
        """Consulta una cita, evento o pedido por su folio.

        Args:
            folio: Folio de la reserva.
        """
        try:
            booking = repo.get_booking(folio)
            if not booking:
                return {
                    "ok": False,
                    "error": {"code": "not_found", "message": f"No existe la reserva {folio}."},
                }
            return {"ok": True, "booking": booking}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    @tool
    def cancel_booking(folio: str) -> dict[str, Any]:
        """Cancela una reserva respetando la política de anticipación.

        Args:
            folio: Folio de la reserva a cancelar.
        """
        try:
            booking = repo.cancel_booking(folio)
            return {"ok": True, "booking": booking}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    @tool
    def reschedule_booking(folio: str, new_start_at: str) -> dict[str, Any]:
        """Reagenda una reserva a una nueva fecha y hora.

        Args:
            folio: Folio de la reserva.
            new_start_at: Nueva fecha y hora ISO-8601.
        """
        try:
            booking = repo.reschedule_booking(folio, new_start_at)
            return {"ok": True, "booking": booking}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    return [
        book_appointment,
        book_event,
        get_booking,
        cancel_booking,
        reschedule_booking,
    ]
