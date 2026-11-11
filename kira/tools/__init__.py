"""Fábrica de tools de Kira, todas ligadas a un repositorio de negocio."""

from __future__ import annotations

from typing import Any

from kira.db.business_repo import BusinessRepository
from kira.tools.availability import build_availability_tool
from kira.tools.bookings import build_booking_tools
from kira.tools.catalog import build_catalog_tool
from kira.tools.faq import build_faq_tool
from kira.tools.orders import build_order_tool
from kira.tools.quotes import build_quote_tools


def build_tools(repo: BusinessRepository) -> list[Any]:
    """Construye la lista de tools que se registran en el agente."""

    return [
        build_faq_tool(repo),
        build_catalog_tool(repo),
        *build_quote_tools(repo),
        build_availability_tool(repo),
        *build_booking_tools(repo),
        build_order_tool(repo),
    ]
