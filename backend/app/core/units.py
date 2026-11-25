"""Cantidades y precio por unidad de medida (€/kg, €/l, €/ud, €/lavado)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .money import Cents, mul_round


class Unit(str, Enum):
    G = "g"
    ML = "ml"
    UD = "ud"
    LAVADO = "lavado"


_ALIASES: dict[str, tuple[Unit, Decimal]] = {
    "g": (Unit.G, Decimal(1)), "gr": (Unit.G, Decimal(1)), "gramo": (Unit.G, Decimal(1)),
    "gramos": (Unit.G, Decimal(1)),
    "kg": (Unit.G, Decimal(1000)), "kilo": (Unit.G, Decimal(1000)),
    "kilos": (Unit.G, Decimal(1000)), "kilogramo": (Unit.G, Decimal(1000)),
    "kilogramos": (Unit.G, Decimal(1000)),
    "ml": (Unit.ML, Decimal(1)), "cl": (Unit.ML, Decimal(10)),
    "l": (Unit.ML, Decimal(1000)), "litro": (Unit.ML, Decimal(1000)),
    "litros": (Unit.ML, Decimal(1000)),
    "ud": (Unit.UD, Decimal(1)), "uds": (Unit.UD, Decimal(1)), "unidad": (Unit.UD, Decimal(1)),
    "unidades": (Unit.UD, Decimal(1)),
    "lavado": (Unit.LAVADO, Decimal(1)), "lavados": (Unit.LAVADO, Decimal(1)),
}


@dataclass(frozen=True)
class Quantity:
    """Cantidad normalizada a unidad base (g, ml, ud, lavado)."""
    amount: Decimal
    unit: Unit

    @classmethod
    def parse(cls, amount: Decimal | int | str, unit: str) -> Quantity:
        key = unit.strip().lower().rstrip(".")
        if key not in _ALIASES:
            raise ValueError(f"Unidad desconocida: {unit!r}")
        base, factor = _ALIASES[key]
        return cls(Decimal(str(amount)) * factor, base)

    def same_dimension(self, other: Quantity) -> bool:
        return self.unit == other.unit


def unit_price(price: Cents, qty: Quantity) -> tuple[Cents, str]:
    """Precio por kg / l / ud / lavado, como exige la normativa de precio unitario."""
    if qty.amount <= 0:
        raise ValueError("Cantidad debe ser > 0")
    if qty.unit == Unit.G:
        return mul_round(price, Decimal(1000) / qty.amount), "€/kg"
    if qty.unit == Unit.ML:
        return mul_round(price, Decimal(1000) / qty.amount), "€/l"
    if qty.unit == Unit.LAVADO:
        return mul_round(price, Decimal(1) / qty.amount), "€/lavado"
    return mul_round(price, Decimal(1) / qty.amount), "€/ud"
