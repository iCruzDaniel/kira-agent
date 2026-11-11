"""Repositorio de negocio: catálogo, FAQ, cotizaciones y agenda."""

from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from kira.db.connection import read_connection, transaction
from kira.errors import ConflictError, NotFoundError, PolicyError, ValidationError
from kira.money import compute_totals, format_money
from kira.time_utils import (
    get_tz,
    iso_utc,
    local_date,
    local_datetime,
    now_iso,
    now_utc,
    parse_datetime,
    to_local,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a",
    "al",
    "algo",
    "como",
    "con",
    "de",
    "del",
    "el",
    "en",
    "es",
    "esta",
    "este",
    "la",
    "las",
    "lo",
    "los",
    "mas",
    "me",
    "mi",
    "mis",
    "no",
    "o",
    "para",
    "pero",
    "por",
    "que",
    "se",
    "si",
    "sin",
    "su",
    "sus",
    "te",
    "ti",
    "tu",
    "tus",
    "un",
    "una",
    "unas",
    "uno",
    "unos",
    "y",
    "ya",
}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(_normalize(text))
        if len(token) > 1 and token not in _STOPWORDS
    }


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


class BusinessRepository:
    """Acceso a db_1. Cada operación abre su propia conexión SQLite."""

    def __init__(self, db_path: Path, tz_name: str = "America/Bogota") -> None:
        self.db_path = db_path
        self.tz_name = tz_name

    # ------------------------------------------------------------------ settings
    def settings(self) -> dict[str, str]:
        with read_connection(self.db_path) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def setting(self, key: str, default: str = "") -> str:
        with read_connection(self.db_path) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def currency(self) -> str:
        return self.setting("currency", "COP")

    def tax_rate(self) -> str:
        return self.setting("tax_rate", "0.19")

    # ------------------------------------------------------------------ FAQ
    def search_faq(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        with read_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, question, answer, keywords, category FROM faq WHERE active = 1"
            ).fetchall()

        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            haystack = f"{row['question']} {row['answer']} {row['keywords']}"
            haystack_tokens = _tokens(haystack)
            overlap = query_tokens & haystack_tokens
            if not overlap:
                continue
            keyword_hits = query_tokens & _tokens(row["keywords"])
            score = len(overlap) / (len(query_tokens) ** 0.5) + 0.5 * len(keyword_hits)
            scored.append(
                (
                    score,
                    {
                        "id": row["id"],
                        "question": row["question"],
                        "answer": row["answer"],
                        "category": row["category"],
                        "score": round(score, 3),
                    },
                )
            )

        scored.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [item[1] for item in scored[: max(1, min(limit, 10))]]

    # ------------------------------------------------------------------ catálogo
    def list_catalog(self, category: str | None = None) -> dict[str, Any]:
        with read_connection(self.db_path) as conn:
            categories = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, name, description FROM categories WHERE active = 1 ORDER BY id"
                )
            ]
            services = [
                dict(row)
                for row in conn.execute(
                    "SELECT s.id, s.category_id, c.name AS category, s.name, s.description, "
                    "s.duration_minutes, s.price_cents FROM services s "
                    "LEFT JOIN categories c ON c.id = s.category_id "
                    "WHERE s.active = 1 ORDER BY s.id"
                )
            ]
            products = [
                dict(row)
                for row in conn.execute(
                    "SELECT p.id, p.category_id, c.name AS category, p.name, p.description, "
                    "p.prep_minutes, p.price_cents FROM products p "
                    "LEFT JOIN categories c ON c.id = p.category_id "
                    "WHERE p.active = 1 ORDER BY p.id"
                )
            ]

        if category:
            wanted = _normalize(category)
            services = [s for s in services if _normalize(s["category"] or "") == wanted]
            products = [p for p in products if _normalize(p["category"] or "") == wanted]
            categories = [c for c in categories if _normalize(c["name"]) == wanted]

        currency = self.currency()
        for item in services + products:
            item["price"] = format_money(item["price_cents"], currency)
        return {"categories": categories, "services": services, "products": products}

    def get_service(self, service_id: int) -> dict[str, Any] | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM services WHERE id = ? AND active = 1", (service_id,)
            ).fetchone()
        return _row_to_dict(row) or None

    def get_product(self, product_id: int) -> dict[str, Any] | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE id = ? AND active = 1", (product_id,)
            ).fetchone()
        return _row_to_dict(row) or None

    def get_resource(self, resource_id: int) -> dict[str, Any] | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM resources WHERE id = ? AND active = 1", (resource_id,)
            ).fetchone()
        return _row_to_dict(row) or None

    def list_resources(self, kind: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM resources WHERE active = 1"
        params: list[Any] = []
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        sql += " ORDER BY id"
        with read_connection(self.db_path) as conn:
            return [dict(row) for row in conn.execute(sql, params)]

    # ------------------------------------------------------------------ horarios
    def _business_hours(self, weekday: int) -> list[dict[str, Any]]:
        with read_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT open_time, close_time FROM business_hours "
                "WHERE weekday = ? AND active = 1 ORDER BY open_time",
                (weekday,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _assert_available(
        self,
        conn: Any,
        kind: str,
        resource: dict[str, Any],
        start_utc: datetime,
        end_utc: datetime,
        party_size: int,
        exclude_folio: str | None = None,
    ) -> int:
        if start_utc <= now_utc():
            raise ValidationError("La fecha y hora deben ser futuras.")

        local_start = to_local(start_utc, self.tz_name)
        local_end = to_local(end_utc, self.tz_name)
        if local_start.date() != local_end.date():
            raise PolicyError("El servicio debe comenzar y terminar el mismo día.")

        hours = self._business_hours(local_start.weekday())
        if not hours:
            raise PolicyError("No hay atención ese día.")

        start_clock = local_start.strftime("%H:%M")
        end_clock = local_end.strftime("%H:%M")
        inside = any(
            block["open_time"] <= start_clock and end_clock <= block["close_time"]
            for block in hours
        )
        if not inside:
            raise PolicyError("El horario solicitado está fuera del horario de atención.")

        if kind == "appointment" and resource["kind"] != "staff":
            raise ValidationError("Las citas deben agendarse con un profesional.")
        if kind == "event":
            if resource["kind"] != "room":
                raise ValidationError("Los eventos deben agendarse en una sala.")
            if party_size > resource["seats"]:
                raise ValidationError(
                    f"La sala admite máximo {resource['seats']} personas; solicitaste {party_size}."
                )
        if kind == "order" and resource["kind"] != "pickup":
            raise ValidationError("Los pedidos deben usar un punto de recogida.")

        overlaps = self._count_overlaps(conn, resource["id"], start_utc, end_utc, exclude_folio)
        if overlaps >= resource["capacity"]:
            raise ConflictError("Ese horario ya está ocupado. Elige otro horario.")
        return resource["capacity"] - overlaps

    def _count_overlaps(
        self,
        conn: Any,
        resource_id: int,
        start_utc: datetime,
        end_utc: datetime,
        exclude_folio: str | None = None,
    ) -> int:
        sql = (
            "SELECT COUNT(*) AS n FROM bookings "
            "WHERE resource_id = ? AND status = 'confirmed' AND start_at < ? AND end_at > ?"
        )
        params: list[Any] = [resource_id, iso_utc(end_utc), iso_utc(start_utc)]
        if exclude_folio:
            sql += " AND folio != ?"
            params.append(exclude_folio)
        return int(conn.execute(sql, params).fetchone()["n"])

    def check_availability(
        self,
        kind: str,
        resource_id: int,
        start_at: str,
        end_at: str,
        party_size: int = 1,
        exclude_folio: str | None = None,
    ) -> dict[str, Any]:
        if kind not in {"appointment", "event", "order"}:
            raise ValidationError("kind debe ser appointment, event u order.")
        resource = self.get_resource(resource_id)
        if not resource:
            raise NotFoundError(f"No existe el recurso {resource_id}.")
        start_utc = parse_datetime(start_at, self.tz_name)
        end_utc = parse_datetime(end_at, self.tz_name)
        with read_connection(self.db_path) as conn:
            remaining = self._assert_available(
                conn, kind, resource, start_utc, end_utc, party_size, exclude_folio
            )
        return {
            "ok": True,
            "resource_id": resource_id,
            "resource_name": resource["name"],
            "start_at": iso_utc(start_utc),
            "end_at": iso_utc(end_utc),
            "start_local": to_local(start_utc, self.tz_name).strftime("%Y-%m-%d %H:%M"),
            "end_local": to_local(end_utc, self.tz_name).strftime("%Y-%m-%d %H:%M"),
            "remaining": remaining,
        }

    def find_available_slots(
        self,
        kind: str,
        date_value: str,
        service_id: int = 0,
        resource_id: int = 0,
        duration_minutes: int = 0,
        party_size: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if kind not in {"appointment", "event", "order"}:
            raise ValidationError("kind debe ser appointment, event u order.")

        day = local_date(date_value, self.tz_name)
        if day < to_local(now_utc(), self.tz_name).date():
            return []

        service: dict[str, Any] | None = None
        if kind == "appointment":
            if not service_id:
                raise ValidationError("service_id es obligatorio para citas.")
            service = self.get_service(service_id)
            if not service:
                raise NotFoundError(f"No existe el servicio {service_id}.")
            duration_minutes = int(service["duration_minutes"])
        else:
            duration_minutes = int(duration_minutes or (60 if kind == "event" else 30))
            if duration_minutes <= 0:
                raise ValidationError("duration_minutes debe ser mayor que cero.")

        resources = self._slots_resources(kind, service_id, resource_id)
        if not resources:
            return []

        step_minutes = int(self.setting("slot_step_minutes", "15") or "15")
        duration = timedelta(minutes=duration_minutes)
        step = timedelta(minutes=step_minutes)
        tz = get_tz(self.tz_name)
        now = now_utc()
        slots: list[dict[str, Any]] = []

        with read_connection(self.db_path) as conn:
            for resource in resources:
                if kind == "event" and party_size > resource["seats"]:
                    continue
                for block in self._business_hours(day.weekday()):
                    cursor = local_datetime(day, block["open_time"], self.tz_name)
                    close = local_datetime(day, block["close_time"], self.tz_name)
                    while cursor + duration <= close:
                        end = cursor + duration
                        if cursor.astimezone(tz) > now:
                            overlaps = self._count_overlaps(conn, resource["id"], cursor, end)
                            if overlaps < resource["capacity"]:
                                slots.append(
                                    {
                                        "start_at": iso_utc(cursor),
                                        "end_at": iso_utc(end),
                                        "start_local": cursor.strftime("%Y-%m-%d %H:%M"),
                                        "end_local": end.strftime("%Y-%m-%d %H:%M"),
                                        "resource_id": resource["id"],
                                        "resource_name": resource["name"],
                                        "remaining": resource["capacity"] - overlaps,
                                    }
                                )
                        cursor += step

        slots.sort(key=lambda slot: (slot["start_at"], slot["resource_id"]))
        return slots[: max(1, min(limit, 100))]

    def _slots_resources(
        self, kind: str, service_id: int, resource_id: int
    ) -> list[dict[str, Any]]:
        if resource_id:
            resource = self.get_resource(resource_id)
            if not resource:
                raise NotFoundError(f"No existe el recurso {resource_id}.")
            return [resource]

        if kind == "appointment":
            with read_connection(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT r.* FROM resources r "
                    "JOIN service_resources sr ON sr.resource_id = r.id "
                    "WHERE sr.service_id = ? AND r.active = 1 AND r.kind = 'staff' "
                    "ORDER BY r.id",
                    (service_id,),
                ).fetchall()
            if rows:
                return [dict(row) for row in rows]
            return self.list_resources("staff")

        return self.list_resources("room" if kind == "event" else "pickup")

    # ------------------------------------------------------------------ cotizaciones
    def _prepare_items(
        self, conn: Any, items: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int]:
        if not items:
            raise ValidationError("La cotización necesita al menos un ítem.")

        lines: list[dict[str, Any]] = []
        subtotal = 0
        for raw in items:
            if not isinstance(raw, dict):
                raise ValidationError("Cada ítem debe ser un objeto JSON.")
            item_type = str(raw.get("item_type", "")).strip().lower()
            if item_type not in {"service", "product"}:
                raise ValidationError("item_type debe ser 'service' o 'product'.")
            try:
                item_id = int(raw.get("item_id", 0))
                quantity = int(raw.get("quantity", 1))
            except (TypeError, ValueError) as exc:
                raise ValidationError("item_id y quantity deben ser enteros.") from exc
            if item_id <= 0 or quantity <= 0:
                raise ValidationError("item_id y quantity deben ser mayores que cero.")

            if item_type == "service":
                row = conn.execute(
                    "SELECT id, name, price_cents, duration_minutes FROM services "
                    "WHERE id = ? AND active = 1",
                    (item_id,),
                ).fetchone()
                duration_minutes = int(row["duration_minutes"] or 0) if row else 0
                prep_minutes = 0
            else:
                row = conn.execute(
                    "SELECT id, name, price_cents, prep_minutes FROM products "
                    "WHERE id = ? AND active = 1",
                    (item_id,),
                ).fetchone()
                duration_minutes = 0
                prep_minutes = int(row["prep_minutes"] or 0) if row else 0

            if not row:
                raise NotFoundError(f"No existe el {item_type} {item_id}.")
            unit_price = int(row["price_cents"])
            line_total = unit_price * quantity
            subtotal += line_total
            lines.append(
                {
                    "item_type": item_type,
                    "item_id": item_id,
                    "description": row["name"],
                    "quantity": quantity,
                    "unit_price_cents": unit_price,
                    "line_total_cents": line_total,
                    "duration_minutes": duration_minutes,
                    "prep_minutes": prep_minutes,
                }
            )
        return lines, subtotal

    def _insert_quote(
        self,
        conn: Any,
        lines: list[dict[str, Any]],
        subtotal: int,
        customer_id: str,
        customer_name: str,
        notes: str,
    ) -> dict[str, Any]:
        settings = self.settings()
        currency = settings.get("currency", "COP")
        tax_rate = settings.get("tax_rate", "0.19")
        valid_days = int(settings.get("quote_valid_days", "7") or "7")
        subtotal, tax, total = compute_totals(subtotal, tax_rate)
        now = now_utc()
        valid_until = now + timedelta(days=valid_days)
        folio = self._new_folio("COT")

        cursor = conn.execute(
            "INSERT INTO quotes(folio, customer_id, customer_name, status, currency, "
            "subtotal_cents, tax_cents, total_cents, notes, valid_until, created_at, updated_at) "
            "VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                folio,
                customer_id,
                customer_name,
                currency,
                subtotal,
                tax,
                total,
                notes,
                iso_utc(valid_until),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        quote_id = int(cursor.lastrowid)
        conn.executemany(
            "INSERT INTO quote_items(quote_id, item_type, item_id, description, quantity, "
            "unit_price_cents, line_total_cents) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    quote_id,
                    line["item_type"],
                    line["item_id"],
                    line["description"],
                    line["quantity"],
                    line["unit_price_cents"],
                    line["line_total_cents"],
                )
                for line in lines
            ],
        )
        return {"id": quote_id, "folio": folio, "total_cents": total}

    def create_quote(
        self,
        items: list[dict[str, Any]],
        customer_id: str = "",
        customer_name: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        with transaction(self.db_path) as conn:
            lines, subtotal = self._prepare_items(conn, items)
            quote = self._insert_quote(conn, lines, subtotal, customer_id, customer_name, notes)
        result = self.get_quote(quote["folio"])
        if not result:
            raise NotFoundError("No se pudo recuperar la cotización recién creada.")
        return result

    def get_quote(self, folio: str) -> dict[str, Any] | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM quotes WHERE folio = ?", (folio,)).fetchone()
            if not row:
                return None
            items = [
                dict(item)
                for item in conn.execute(
                    "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id", (row["id"],)
                )
            ]
        quote = dict(row)
        quote["items"] = items
        currency = quote["currency"]
        quote["subtotal"] = format_money(quote["subtotal_cents"], currency)
        quote["tax"] = format_money(quote["tax_cents"], currency)
        quote["total"] = format_money(quote["total_cents"], currency)
        quote["valid_until_local"] = to_local(
            parse_datetime(quote["valid_until"], self.tz_name), self.tz_name
        ).strftime("%Y-%m-%d %H:%M")
        return quote

    # ------------------------------------------------------------------ agenda
    def create_booking(
        self,
        kind: str,
        resource_id: int,
        start_at: str,
        customer_name: str,
        customer_id: str = "",
        customer_phone: str = "",
        service_id: int = 0,
        duration_minutes: int = 0,
        party_size: int = 1,
        notes: str = "",
        quote_id: int | None = None,
    ) -> dict[str, Any]:
        if not customer_name.strip():
            raise ValidationError("El nombre del cliente es obligatorio.")
        if kind not in {"appointment", "event", "order"}:
            raise ValidationError("kind debe ser appointment, event u order.")

        resource = self.get_resource(resource_id)
        if not resource:
            raise NotFoundError(f"No existe el recurso {resource_id}.")

        service: dict[str, Any] | None = None
        if kind == "appointment":
            if not service_id:
                raise ValidationError("service_id es obligatorio para citas.")
            service = self.get_service(service_id)
            if not service:
                raise NotFoundError(f"No existe el servicio {service_id}.")
            duration_minutes = int(service["duration_minutes"])
            with read_connection(self.db_path) as conn:
                link_count = conn.execute(
                    "SELECT COUNT(*) AS n FROM service_resources WHERE service_id = ?",
                    (service_id,),
                ).fetchone()["n"]
                linked = conn.execute(
                    "SELECT 1 FROM service_resources WHERE service_id = ? AND resource_id = ?",
                    (service_id, resource_id),
                ).fetchone()
            if link_count and not linked:
                raise ValidationError(
                    f"{resource['name']} no atiende el servicio {service['name']}."
                )
        else:
            if duration_minutes <= 0:
                raise ValidationError("duration_minutes debe ser mayor que cero.")

        start_utc = parse_datetime(start_at, self.tz_name)
        end_utc = start_utc + timedelta(minutes=duration_minutes)
        folio = self._new_folio("CIT" if kind == "appointment" else "EVT" if kind == "event" else "BKG")
        now = now_utc().isoformat()

        with transaction(self.db_path) as conn:
            self._assert_available(
                conn, kind, resource, start_utc, end_utc, party_size
            )
            conn.execute(
                "INSERT INTO bookings(folio, kind, customer_id, customer_name, customer_phone, "
                "resource_id, service_id, party_size, start_at, end_at, status, notes, quote_id, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?, ?, ?)",
                (
                    folio,
                    kind,
                    customer_id,
                    customer_name,
                    customer_phone,
                    resource_id,
                    service_id or None,
                    party_size,
                    iso_utc(start_utc),
                    iso_utc(end_utc),
                    notes,
                    quote_id,
                    now,
                    now,
                ),
            )
        result = self.get_booking(folio)
        if not result:
            raise NotFoundError("No se pudo recuperar la reserva recién creada.")
        return result

    def get_booking(self, folio: str) -> dict[str, Any] | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT b.*, r.name AS resource_name, r.kind AS resource_kind, "
                "s.name AS service_name FROM bookings b "
                "JOIN resources r ON r.id = b.resource_id "
                "LEFT JOIN services s ON s.id = b.service_id "
                "WHERE b.folio = ?",
                (folio,),
            ).fetchone()
        if not row:
            return None
        booking = dict(row)
        start_utc = parse_datetime(booking["start_at"], self.tz_name)
        end_utc = parse_datetime(booking["end_at"], self.tz_name)
        booking["start_local"] = to_local(start_utc, self.tz_name).strftime("%Y-%m-%d %H:%M")
        booking["end_local"] = to_local(end_utc, self.tz_name).strftime("%Y-%m-%d %H:%M")
        return booking

    def cancel_booking(self, folio: str) -> dict[str, Any]:
        hours = int(self.setting("cancellation_hours", "24") or "24")
        with transaction(self.db_path) as conn:
            row = conn.execute("SELECT * FROM bookings WHERE folio = ?", (folio,)).fetchone()
            if not row:
                raise NotFoundError(f"No existe la reserva {folio}.")
            if row["status"] != "confirmed":
                raise PolicyError(f"La reserva {folio} no está activa.")
            start_utc = parse_datetime(row["start_at"], self.tz_name)
            if start_utc - now_utc() < timedelta(hours=hours):
                raise PolicyError(
                    f"Solo se puede cancelar con al menos {hours} horas de anticipación."
                )
            now = now_utc().isoformat()
            conn.execute(
                "UPDATE bookings SET status = 'cancelled', updated_at = ? WHERE folio = ?",
                (now, folio),
            )
            conn.execute(
                "UPDATE orders SET status = 'cancelled', updated_at = ? WHERE booking_id = ?",
                (now, row["id"]),
            )
        result = self.get_booking(folio)
        if not result:
            raise NotFoundError(f"No existe la reserva {folio}.")
        return result

    def reschedule_booking(self, folio: str, new_start_at: str) -> dict[str, Any]:
        hours = int(self.setting("cancellation_hours", "24") or "24")
        with transaction(self.db_path) as conn:
            row = conn.execute("SELECT * FROM bookings WHERE folio = ?", (folio,)).fetchone()
            if not row:
                raise NotFoundError(f"No existe la reserva {folio}.")
            if row["status"] != "confirmed":
                raise PolicyError(f"La reserva {folio} no está activa.")
            old_start = parse_datetime(row["start_at"], self.tz_name)
            old_end = parse_datetime(row["end_at"], self.tz_name)
            if old_start - now_utc() < timedelta(hours=hours):
                raise PolicyError(
                    f"Solo se puede reagendar con al menos {hours} horas de anticipación."
                )
            resource = self.get_resource(row["resource_id"])
            if not resource:
                raise NotFoundError("El recurso de la reserva ya no está disponible.")
            new_start = parse_datetime(new_start_at, self.tz_name)
            new_end = new_start + (old_end - old_start)
            self._assert_available(
                conn,
                row["kind"],
                resource,
                new_start,
                new_end,
                row["party_size"],
                exclude_folio=folio,
            )
            conn.execute(
                "UPDATE bookings SET start_at = ?, end_at = ?, updated_at = ? WHERE folio = ?",
                (iso_utc(new_start), iso_utc(new_end), now_utc().isoformat(), folio),
            )
        result = self.get_booking(folio)
        if not result:
            raise NotFoundError(f"No existe la reserva {folio}.")
        return result

    def list_bookings(
        self, date_value: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        sql = (
            "SELECT b.*, r.name AS resource_name, r.kind AS resource_kind, "
            "s.name AS service_name FROM bookings b "
            "JOIN resources r ON r.id = b.resource_id "
            "LEFT JOIN services s ON s.id = b.service_id WHERE 1 = 1"
        )
        params: list[Any] = []
        if date_value:
            day = local_date(date_value, self.tz_name)
            start_local = datetime.combine(day, time.min, tzinfo=get_tz(self.tz_name))
            end_local = start_local + timedelta(days=1)
            sql += " AND b.start_at >= ? AND b.start_at < ?"
            params.extend([iso_utc(start_local), iso_utc(end_local)])
        if status:
            sql += " AND b.status = ?"
            params.append(status)
        sql += " ORDER BY b.start_at, b.id"
        with read_connection(self.db_path) as conn:
            rows = [dict(row) for row in conn.execute(sql, params)]
        for booking in rows:
            start_utc = parse_datetime(booking["start_at"], self.tz_name)
            end_utc = parse_datetime(booking["end_at"], self.tz_name)
            booking["start_local"] = to_local(start_utc, self.tz_name).strftime("%Y-%m-%d %H:%M")
            booking["end_local"] = to_local(end_utc, self.tz_name).strftime("%Y-%m-%d %H:%M")
        return rows

    # ------------------------------------------------------------------ pedidos
    def create_order(
        self,
        items: list[dict[str, Any]],
        pickup_at: str,
        customer_name: str,
        customer_id: str = "",
        customer_phone: str = "",
        fulfillment: str = "pickup",
        delivery_address: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        if not customer_name.strip():
            raise ValidationError("El nombre del cliente es obligatorio.")
        if fulfillment not in {"pickup", "delivery"}:
            raise ValidationError("fulfillment debe ser 'pickup' o 'delivery'.")
        if fulfillment == "delivery" and not delivery_address.strip():
            raise ValidationError("La dirección es obligatoria para entrega a domicilio.")

        resource = next(iter(self.list_resources("pickup")), None)
        if not resource:
            raise NotFoundError("No hay punto de recogida configurado.")

        start_utc = parse_datetime(pickup_at, self.tz_name)
        order_folio = self._new_folio("PED")
        booking_folio = self._new_folio("BKG")
        now = now_utc().isoformat()

        with transaction(self.db_path) as conn:
            lines, subtotal = self._prepare_items(conn, items)
            quote = self._insert_quote(conn, lines, subtotal, customer_id, customer_name, notes)
            prep_minutes = max(
                (int(line["prep_minutes"] or 0) for line in lines), default=30
            ) or 30
            end_utc = start_utc + timedelta(minutes=prep_minutes)
            self._assert_available(conn, "order", resource, start_utc, end_utc, 1)
            conn.execute(
                "INSERT INTO bookings(folio, kind, customer_id, customer_name, customer_phone, "
                "resource_id, service_id, party_size, start_at, end_at, status, notes, quote_id, "
                "created_at, updated_at) VALUES (?, 'order', ?, ?, ?, ?, NULL, 1, ?, ?, "
                "'confirmed', ?, ?, ?, ?)",
                (
                    booking_folio,
                    customer_id,
                    customer_name,
                    customer_phone,
                    resource["id"],
                    iso_utc(start_utc),
                    iso_utc(end_utc),
                    notes,
                    quote["id"],
                    now,
                    now,
                ),
            )
            booking_id = int(
                conn.execute(
                    "SELECT id FROM bookings WHERE folio = ?", (booking_folio,)
                ).fetchone()["id"]
            )
            conn.execute(
                "INSERT INTO orders(folio, booking_id, quote_id, customer_id, fulfillment, "
                "delivery_address, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?, ?)",
                (
                    order_folio,
                    booking_id,
                    quote["id"],
                    customer_id,
                    fulfillment,
                    delivery_address,
                    now,
                    now,
                ),
            )
            order_id = int(
                conn.execute("SELECT id FROM orders WHERE folio = ?", (order_folio,)).fetchone()["id"]
            )
            conn.executemany(
                "INSERT INTO order_items(order_id, item_type, item_id, description, quantity, "
                "unit_price_cents, line_total_cents) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        order_id,
                        line["item_type"],
                        line["item_id"],
                        line["description"],
                        line["quantity"],
                        line["unit_price_cents"],
                        line["line_total_cents"],
                    )
                    for line in lines
                ],
            )

        result = self.get_order(order_folio)
        if not result:
            raise NotFoundError("No se pudo recuperar el pedido recién creado.")
        return result

    def get_order(self, folio: str) -> dict[str, Any] | None:
        with read_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT o.*, b.folio AS booking_folio, b.start_at, b.end_at, "
                "b.resource_id, r.name AS resource_name, q.folio AS quote_folio, "
                "q.subtotal_cents, q.tax_cents, q.total_cents, q.currency "
                "FROM orders o JOIN bookings b ON b.id = o.booking_id "
                "JOIN resources r ON r.id = b.resource_id "
                "LEFT JOIN quotes q ON q.id = o.quote_id WHERE o.folio = ?",
                (folio,),
            ).fetchone()
            if not row:
                return None
            items = [
                dict(item)
                for item in conn.execute(
                    "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (row["id"],)
                )
            ]
        order = dict(row)
        order["items"] = items
        currency = order.get("currency") or self.currency()
        order["subtotal"] = format_money(order["subtotal_cents"], currency)
        order["tax"] = format_money(order["tax_cents"], currency)
        order["total"] = format_money(order["total_cents"], currency)
        start_utc = parse_datetime(order["start_at"], self.tz_name)
        end_utc = parse_datetime(order["end_at"], self.tz_name)
        order["pickup_local"] = to_local(start_utc, self.tz_name).strftime("%Y-%m-%d %H:%M")
        order["end_local"] = to_local(end_utc, self.tz_name).strftime("%Y-%m-%d %H:%M")
        return order

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _new_folio(prefix: str) -> str:
        return f"{prefix}-{now_utc():%Y%m%d}-{secrets.token_hex(3).upper()}"
