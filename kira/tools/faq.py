"""Tool de búsqueda en preguntas frecuentes."""

from __future__ import annotations

from typing import Any

from strands import tool

from kira.db.business_repo import BusinessRepository
from kira.tools._common import failure


def build_faq_tool(repo: BusinessRepository):
    @tool
    def faq_search(query: str, limit: int = 5) -> dict[str, Any]:
        """Busca en las preguntas frecuentes del negocio.

        Úsala para horarios, ubicación, formas de pago, políticas de cancelación,
        vigencia de cotizaciones, domicilios y servicios.

        Args:
            query: Pregunta del cliente o palabras clave.
            limit: Número máximo de respuestas a devolver (1-10).
        """
        try:
            results = repo.search_faq(query, limit)
            return {"ok": True, "count": len(results), "results": results}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    return faq_search
