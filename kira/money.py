"""Cálculos monetarios con enteros en centavos y redondeo comercial."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def compute_totals(subtotal_cents: int, tax_rate: str) -> tuple[int, int, int]:
    """Devuelve (subtotal, impuesto, total) en centavos."""

    rate = Decimal(str(tax_rate))
    tax = (Decimal(subtotal_cents) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    tax_cents = int(tax)
    return subtotal_cents, tax_cents, subtotal_cents + tax_cents


def format_money(cents: int, currency: str = "COP") -> str:
    amount = Decimal(cents) / Decimal(100)
    if currency == "COP":
        return f"${amount:,.0f} COP".replace(",", ".")
    return f"${amount:,.2f} {currency}"
