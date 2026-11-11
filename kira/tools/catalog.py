"""Tool de consulta del catálogo."""

from __future__ import annotations

from typing import Any

from strands import tool

from kira.db.business_repo import BusinessRepository
from kira.tools._common import failure


def build_catalog_tool(repo: BusinessRepository):
    @tool
    def list_catalog(category: str = "") -> dict[str, Any]:
        """Lista categorías, servicios y productos con sus precios.

        Args:
            category: Nombre de categoría para filtrar; vacío devuelve todo.
        """
        try:
            catalog = repo.list_catalog(category or None)
            return {"ok": True, **catalog}
        except Exception as exc:  # noqa: BLE001 - frontera de tool
            return failure(exc)

    return list_catalog
