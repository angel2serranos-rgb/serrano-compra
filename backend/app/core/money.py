"""Importes monetarios en céntimos enteros. Nunca float.

Regla de redondeo: medio hacia arriba (ROUND_HALF_UP) al céntimo.
OJO: cada cadena puede redondear distinto en sus promociones; si un ticket
real contradice este redondeo, se registra la diferencia (no se oculta).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

Cents = int


def to_cents(value: str | int | Decimal) -> Cents:
    """'1,99' | '1.99' | Decimal('1.99') -> 199. Rechaza float a propósito."""
    if isinstance(value, float):
        raise TypeError("No se admiten float para dinero; usa str o Decimal")
    if isinstance(value, int):
        return value * 100
    if isinstance(value, str):
        value = value.strip().replace("€", "").replace(" ", "")
        if "," in value:  # formato ES: 1.234,56
            value = value.replace(".", "").replace(",", ".")
        value = Decimal(value)
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def mul_round(cents: Cents, factor: Decimal | str) -> Cents:
    """Multiplica céntimos por un factor y redondea al céntimo (half-up)."""
    result = Decimal(cents) * Decimal(factor)
    return int(result.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fmt_eur(cents: Cents) -> str:
    """199 -> '1,99 €'; 123456 -> '1.234,56 €'; -50 -> '-0,50 €'."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    euros, cent = divmod(cents, 100)
    euros_txt = f"{euros:,}".replace(",", ".")
    return f"{sign}{euros_txt},{cent:02d} €"
