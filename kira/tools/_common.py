"""Utilidades compartidas por las tools."""

from __future__ import annotations

import json
from typing import Any

from kira.errors import KiraError, ValidationError


def failure(exc: Exception) -> dict[str, Any]:
    """Convierte una excepción en una respuesta estructurada para el modelo."""

    code = exc.code if isinstance(exc, KiraError) else "internal_error"
    return {"ok": False, "error": {"code": code, "message": str(exc)}}


def parse_items(items_json: str) -> list[dict[str, Any]]:
    """Parsea y valida la lista JSON de ítems de una cotización o pedido."""

    try:
        parsed = json.loads(items_json)
    except json.JSONDecodeError as exc:
        raise ValidationError("items_json no es JSON válido.") from exc
    if not isinstance(parsed, list):
        raise ValidationError("items_json debe ser una lista JSON.")
    return parsed
